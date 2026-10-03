using System;
using UnityEngine;
using UnityEngine.UI;

namespace DroneThreatTrainer.Simulation
{
    /// <summary>
    /// Trainee interaction manager (Section 10).
    /// Allows trainees to select simulated objects, classify them, and submit predefined responses.
    /// </summary>
    public class TraineeInterfaceController : MonoBehaviour
    {
        [Header("UI Panels")]
        [SerializeField] private Text scenarioInfoText;
        [SerializeField] private Text timerText;
        [SerializeField] private Text statusText;
        [SerializeField] private Text selectedTargetText;

        [Header("Active Session State")]
        public string currentSessionCode = "SES_001";
        public DroneController selectedDrone;
        private float sessionStartTime;
        private bool isSessionActive = false;

        private void Start()
        {
            sessionStartTime = Time.time;
            isSessionActive = true;
            UpdateStatus("SIMULATION ACTIVE :: RADAR SCANNING");
        }

        private void Update()
        {
            if (isSessionActive)
            {
                float elapsed = Time.time - sessionStartTime;
                int minutes = (int)(elapsed / 60);
                int seconds = (int)(elapsed % 60);
                if (timerText != null) timerText.text = $"TIME: {minutes:D2}:{seconds:D2}";

                // Allow clicking in viewport to select target
                HandleMouseSelection();
            }
        }

        private void HandleMouseSelection()
        {
            if (Input.GetMouseButtonDown(0))
            {
                Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
                if (Physics.Raycast(ray, out RaycastHit hit, 200f))
                {
                    DroneController drone = hit.collider.GetComponentInParent<DroneController>();
                    if (drone != null)
                    {
                        SelectTarget(drone);
                    }
                }
            }
        }

        public void SelectTarget(DroneController drone)
        {
            selectedDrone = drone;
            string text = $"SELECTED: TARGET ID {drone.targetId:D2} (CLASS: {drone.targetClass.ToUpper()})";
            if (selectedTargetText != null) selectedTargetText.text = text;
            UpdateStatus($"Target ID {drone.targetId:D2} Locked");
        }

        #region Predefined Training Action Buttons (Section 10)

        /// <summary>
        /// [DETECT] button: Trainee declares an aerial object spotted.
        /// </summary>
        public void OnDetectButtonPressed()
        {
            if (selectedDrone == null)
            {
                UpdateStatus("WARNING: No target selected! Click a target first.");
                return;
            }
            SubmitAction("detect", true);
            UpdateStatus($"Object {selectedDrone.targetId:D2} Marked as Detected");
        }

        /// <summary>
        /// [IDENTIFY] button: Trainee confirms classification (e.g. Drone vs Bird).
        /// </summary>
        public void OnIdentifyButtonPressed()
        {
            if (selectedDrone == null) return;
            string actionName = $"classify_{selectedDrone.targetClass.ToLower()}";
            SubmitAction(actionName, true);
            UpdateStatus($"Target ID {selectedDrone.targetId:D2} Identified as {selectedDrone.targetClass.ToUpper()}");
        }

        /// <summary>
        /// [TRACK] button: Trainee commits target to persistent tracking queue.
        /// </summary>
        public void OnTrackButtonPressed()
        {
            if (selectedDrone == null) return;
            SubmitAction("commit_tracking", true);
            UpdateStatus($"Target ID {selectedDrone.targetId:D2} Added to Priority Tracking");
        }

        /// <summary>
        /// [RESPOND] button: Trainee initiates non-kinetic electronic countermeasure (RF Jamming / Alert).
        /// Note: As required by safety rules, only predefined simulation responses are provided.
        /// </summary>
        public void OnRespondButtonPressed()
        {
            if (selectedDrone == null) return;
            // Predefined training responses
            SubmitAction("respond_jam_rf", true);
            UpdateStatus($"Predefined Response Triggered: RF Disruption protocol initiated on Target {selectedDrone.targetId:D2}");
        }

        private async void SubmitAction(string actionName, bool correct)
        {
            if (selectedDrone == null || NetworkClient.Instance == null) return;

            float respTime = UnityEngine.Random.Range(1.5f, 4.0f);
            float simTime = Time.time - sessionStartTime;

            string json = $"{{\"session_code\":\"{currentSessionCode}\",\"object_id\":{selectedDrone.targetId},\"action\":\"{actionName}\",\"timestamp\":{simTime:F2},\"correct\":{correct.ToString().ToLower()},\"response_time\":{respTime:F2}}}";

            try
            {
                await NetworkClient.Instance.PostJsonAsync("actions", json);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[TraineeInterface] Failed to record action: {ex.Message}");
            }
        }

        private void UpdateStatus(string message)
        {
            if (statusText != null) statusText.text = message;
            Debug.Log($"[TraineeInterface] {message}");
        }

        #endregion
    }
}
