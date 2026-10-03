using System;
using System.Collections.Generic;
using UnityEngine;

namespace DroneThreatTrainer.Simulation
{
    public enum FlightPattern
    {
        DirectPatrol,
        SinusoidalBob,
        ZigzagEvasion,
        Hover
    }

    /// <summary>
    /// Simulates quadcopter drone flight dynamics, waypoints, rotor spinning, and screen-space projections.
    /// </summary>
    public class DroneController : MonoBehaviour
    {
        [Header("Target Metadata")]
        public int targetId;
        public string targetClass = "drone";
        public bool isThreat = true;

        [Header("Flight Parameters")]
        [SerializeField] private float flightSpeed = 8.0f;
        [SerializeField] private float turnSpeed = 3.0f;
        [SerializeField] private float bobAmplitude = 0.5f;
        [SerializeField] private float bobFrequency = 1.5f;
        [SerializeField] private FlightPattern flightPattern = FlightPattern.SinusoidalBob;

        [Header("Waypoints")]
        private List<Vector3> waypoints = new List<Vector3>();
        private int currentWaypointIndex = 0;
        private float initialY;
        private float timeOffset;

        private void Start()
        {
            initialY = transform.position.y;
            timeOffset = UnityEngine.Random.Range(0f, 10f);
        }

        public void Initialize(int id, string classification, List<Vector3> pathWaypoints, float speed, FlightPattern pattern)
        {
            targetId = id;
            targetClass = classification;
            waypoints = pathWaypoints ?? new List<Vector3>();
            flightSpeed = speed;
            flightPattern = pattern;
            currentWaypointIndex = 0;
        }

        private void Update()
        {
            MoveAlongWaypoints();
            ApplySecondaryMotion();
        }

        private void MoveAlongWaypoints()
        {
            if (waypoints == null || waypoints.Count == 0) return;

            Vector3 targetPos = waypoints[currentWaypointIndex];
            Vector3 moveDir = (targetPos - transform.position).normalized;

            // Rotate towards target heading
            if (moveDir != Vector3.zero)
            {
                Quaternion targetRot = Quaternion.LookRotation(moveDir);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRot, turnSpeed * Time.deltaTime);
            }

            // Translate forward
            transform.position += transform.forward * (flightSpeed * Time.deltaTime);

            // Check waypoint proximity
            if (Vector3.Distance(transform.position, targetPos) < 2.0f)
            {
                currentWaypointIndex = (currentWaypointIndex + 1) % waypoints.Count;
            }
        }

        private void ApplySecondaryMotion()
        {
            float t = Time.time + timeOffset;
            Vector3 pos = transform.position;

            switch (flightPattern)
            {
                case FlightPattern.SinusoidalBob:
                    pos.y = initialY + Mathf.Sin(t * bobFrequency) * bobAmplitude;
                    transform.position = pos;
                    break;

                case FlightPattern.ZigzagEvasion:
                    float lateralOffset = Mathf.Cos(t * 2.5f) * 1.5f * Time.deltaTime;
                    transform.position += transform.right * lateralOffset;
                    break;
            }
        }

        /// <summary>
        /// Projects the drone's 3D bounding volume to screen coordinates [x1, y1, x2, y2].
        /// </summary>
        public Rect GetScreenBoundingBox(Camera cam)
        {
            Renderer rend = GetComponentInChildren<Renderer>();
            Bounds bounds = rend != null ? rend.bounds : new Bounds(transform.position, Vector3.one * 1.5f);

            Vector3[] corners = new Vector3[8];
            Vector3 min = bounds.min;
            Vector3 max = bounds.max;

            corners[0] = new Vector3(min.x, min.y, min.z);
            corners[1] = new Vector3(max.x, min.y, min.z);
            corners[2] = new Vector3(min.x, max.y, min.z);
            corners[3] = new Vector3(max.x, max.y, min.z);
            corners[4] = new Vector3(min.x, min.y, max.z);
            corners[5] = new Vector3(max.x, min.y, max.z);
            corners[6] = new Vector3(min.x, max.y, max.z);
            corners[7] = new Vector3(max.x, max.y, max.z);

            float minX = float.MaxValue, minY = float.MaxValue;
            float maxX = float.MinValue, maxY = float.MinValue;

            for (int i = 0; i < 8; i++)
            {
                Vector3 screenPoint = cam.WorldToScreenPoint(corners[i]);
                if (screenPoint.z > 0)
                {
                    minX = Mathf.Min(minX, screenPoint.x);
                    minY = Mathf.Min(minY, screenPoint.y);
                    maxX = Mathf.Max(maxX, screenPoint.x);
                    maxY = Mathf.Max(maxY, screenPoint.y);
                }
            }

            // Convert to top-left origin (standard image/OpenCV coordinates)
            float topY = Screen.height - maxY;
            float height = maxY - minY;
            return new Rect(minX, topY, maxX - minX, height);
        }
    }
}
