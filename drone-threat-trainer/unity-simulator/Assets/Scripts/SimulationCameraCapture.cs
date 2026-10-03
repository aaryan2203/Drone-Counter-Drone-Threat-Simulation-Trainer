using System;
using System.Collections;
using System.Text;
using UnityEngine;

namespace DroneThreatTrainer.Simulation
{
    /// <summary>
    /// Captures simulation camera frames into textures, compresses them,
    /// and streams them to the AI pipeline via WebSocket.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class SimulationCameraCapture : MonoBehaviour
    {
        [Header("Capture Settings")]
        [SerializeField] private int captureWidth = 640;
        [SerializeField] private int captureHeight = 480;
        [SerializeField] private int targetFps = 15;
        [SerializeField] private int jpegQuality = 70;
        [SerializeField] private bool streamEnabled = true;

        private Camera simCamera;
        private RenderTexture renderTexture;
        private Texture2D capturedTexture;
        private Rect rect;
        private float captureInterval;
        private float lastCaptureTime;

        private void Start()
        {
            simCamera = GetComponent<Camera>();
            captureInterval = 1.0f / targetFps;

            renderTexture = new RenderTexture(captureWidth, captureHeight, 24, RenderTextureFormat.ARGB32);
            capturedTexture = new Texture2D(captureWidth, captureHeight, TextureFormat.RGB24, false);
            rect = new Rect(0, 0, captureWidth, captureHeight);

            simCamera.targetTexture = renderTexture;
        }

        private void OnDestroy()
        {
            if (renderTexture != null) renderTexture.Release();
            if (capturedTexture != null) Destroy(capturedTexture);
        }

        private void LateUpdate()
        {
            if (!streamEnabled) return;

            if (Time.time - lastCaptureTime >= captureInterval)
            {
                lastCaptureTime = Time.time;
                CaptureAndStreamFrame();
            }
        }

        private void CaptureAndStreamFrame()
        {
            RenderTexture prev = RenderTexture.active;
            RenderTexture.active = renderTexture;

            capturedTexture.ReadPixels(rect, 0, 0);
            capturedTexture.Apply();

            RenderTexture.active = prev;

            byte[] jpegBytes = capturedTexture.EncodeToJPG(jpegQuality);
            string base64Frame = Convert.ToBase64String(jpegBytes);

            // Transmit frame to telemetry hub
            if (NetworkClient.Instance != null)
            {
                string payload = $"{{\"event\":\"sim_frame\",\"timestamp\":{Time.time:F2},\"frame_base64\":\"{base64Frame}\"}}";
                _ = NetworkClient.Instance.SendWebSocketEventAsync(payload);
            }
        }
    }
}
