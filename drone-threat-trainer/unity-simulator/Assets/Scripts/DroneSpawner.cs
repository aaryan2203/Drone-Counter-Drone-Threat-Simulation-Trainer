using System;
using System.Collections.Generic;
using UnityEngine;

namespace DroneThreatTrainer.Simulation
{
    [Serializable]
    public class ScenarioData
    {
        public string scenario_code;
        public string environment;
        public string lighting;
        public string visibility;
        public string difficulty;
        public int object_count;
        public int seed;
        public int duration;
    }

    /// <summary>
    /// Procedurally spawns drones and airborne objects according to scenario specifications.
    /// </summary>
    public class DroneSpawner : MonoBehaviour
    {
        [Header("Prefabs")]
        [SerializeField] private GameObject dronePrefab;
        [SerializeField] private GameObject birdPrefab;
        [SerializeField] private GameObject aircraftPrefab;

        [Header("Spawn Bounds")]
        [SerializeField] private Vector3 spawnCenter = new Vector3(0, 25, 60);
        [SerializeField] private Vector3 spawnExtents = new Vector3(40, 15, 30);

        private List<DroneController> activeDrones = new List<DroneController>();

        public List<DroneController> ActiveDrones => activeDrones;

        public void SpawnScenarioObjects(ScenarioData scenario)
        {
            ClearExistingObjects();

            UnityEngine.Random.InitState(scenario.seed);
            int count = scenario.object_count > 0 ? scenario.object_count : 4;

            for (int i = 0; i < count; i++)
            {
                int targetId = i + 1;
                string targetClass = DetermineObjectClass(i, count);
                GameObject prefab = GetPrefabForClass(targetClass);

                Vector3 startPos = GetRandomPositionWithinBounds();
                GameObject instance = null;

                if (prefab != null)
                {
                    instance = Instantiate(prefab, startPos, Quaternion.identity, transform);
                }
                else
                {
                    // Fallback: Procedurally create a drone visual using primitives
                    instance = CreateProceduralDroneObject(startPos);
                }

                DroneController controller = instance.GetComponent<DroneController>();
                if (controller == null)
                {
                    controller = instance.AddComponent<DroneController>();
                }

                List<Vector3> waypoints = GenerateWaypoints(startPos, 4);
                float speed = UnityEngine.Random.Range(6.0f, 12.0f);
                FlightPattern pattern = (FlightPattern)UnityEngine.Random.Range(0, 3);

                controller.Initialize(targetId, targetClass, waypoints, speed, pattern);
                activeDrones.Add(controller);
            }

            Debug.Log($"[DroneSpawner] Spawned {activeDrones.Count} objects for Scenario {scenario.scenario_code} (Difficulty: {scenario.difficulty})");
        }

        private string DetermineObjectClass(int index, int total)
        {
            // Majority are drones; occasional bird or commercial aircraft
            if (index == 0) return "drone";
            float r = UnityEngine.Random.value;
            if (r < 0.65f) return "drone";
            if (r < 0.85f) return "bird";
            return "aircraft";
        }

        private GameObject GetPrefabForClass(string targetClass)
        {
            switch (targetClass.ToLower())
            {
                case "drone": return dronePrefab;
                case "bird": return birdPrefab;
                case "aircraft": return aircraftPrefab;
                default: return dronePrefab;
            }
        }

        private Vector3 GetRandomPositionWithinBounds()
        {
            return spawnCenter + new Vector3(
                UnityEngine.Random.Range(-spawnExtents.x, spawnExtents.x),
                UnityEngine.Random.Range(-spawnExtents.y, spawnExtents.y),
                UnityEngine.Random.Range(-spawnExtents.z, spawnExtents.z)
            );
        }

        private List<Vector3> GenerateWaypoints(Vector3 origin, int count)
        {
            List<Vector3> pts = new List<Vector3> { origin };
            for (int i = 0; i < count; i++)
            {
                pts.Add(GetRandomPositionWithinBounds());
            }
            return pts;
        }

        private GameObject CreateProceduralDroneObject(Vector3 position)
        {
            GameObject droneObj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            droneObj.name = "SimulatedQuadcopter";
            droneObj.transform.position = position;
            droneObj.transform.localScale = new Vector3(1.2f, 0.3f, 1.2f);

            // Add center camera pod
            GameObject pod = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            pod.transform.SetParent(droneObj.transform);
            pod.transform.localPosition = new Vector3(0, -0.4f, 0.2f);
            pod.transform.localScale = new Vector3(0.4f, 0.4f, 0.4f);

            return droneObj;
        }

        public void ClearExistingObjects()
        {
            foreach (var drone in activeDrones)
            {
                if (drone != null) Destroy(drone.gameObject);
            }
            activeDrones.Clear();
        }
    }
}
