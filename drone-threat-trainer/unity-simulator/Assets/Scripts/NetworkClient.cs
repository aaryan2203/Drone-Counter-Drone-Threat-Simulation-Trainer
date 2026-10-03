using System;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.WebSockets;
using UnityEngine;
using UnityEngine.Networking;

namespace DroneThreatTrainer.Simulation
{
    /// <summary>
    /// Communicates with FastAPI backend via REST and WebSocket.
    /// Manages session start/end, detection events, trainee actions, and telemetry broadcast.
    /// </summary>
    public class NetworkClient : MonoBehaviour
    {
        public static NetworkClient Instance { get; private set; }

        [Header("Backend Configuration")]
        [SerializeField] private string apiBaseUrl = "http://127.0.0.1:8000/api";
        [SerializeField] private string wsTelemetryUrl = "ws://127.0.0.1:8000/ws/telemetry";
        [SerializeField] private bool autoConnectWebSocket = true;

        private ClientWebSocket webSocket;
        private CancellationTokenSource cancellationTokenSource;

        public event Action<string> OnWebSocketMessageReceived;
        public event Action OnWebSocketConnected;
        public event Action<string> OnWebSocketError;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private async void Start()
        {
            if (autoConnectWebSocket)
            {
                await ConnectWebSocketAsync();
            }
        }

        private void OnDestroy()
        {
            DisconnectWebSocket();
        }

        #region WebSocket Communication

        public async Task ConnectWebSocketAsync()
        {
            try
            {
                cancellationTokenSource = new CancellationTokenSource();
                webSocket = new ClientWebSocket();
                Uri uri = new Uri(wsTelemetryUrl);

                await webSocket.ConnectAsync(uri, cancellationTokenSource.Token);
                Debug.Log($"[NetworkClient] Connected to Telemetry WebSocket at {wsTelemetryUrl}");
                OnWebSocketConnected?.Invoke();

                _ = ReceiveWebSocketMessagesAsync();
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[NetworkClient] WebSocket connection failed: {ex.Message}");
                OnWebSocketError?.Invoke(ex.Message);
            }
        }

        private async Task ReceiveWebSocketMessagesAsync()
        {
            byte[] buffer = new byte[8192];
            try
            {
                while (webSocket != null && webSocket.State == WebSocketState.Open)
                {
                    WebSocketReceiveResult result = await webSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer),
                        cancellationTokenSource.Token
                    );

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                        break;
                    }

                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    OnWebSocketMessageReceived?.Invoke(message);
                }
            }
            catch (Exception ex) when (!(ex is OperationCanceledException))
            {
                Debug.LogWarning($"[NetworkClient] WebSocket receive error: {ex.Message}");
            }
        }

        public async Task SendWebSocketEventAsync(string jsonPayload)
        {
            if (webSocket == null || webSocket.State != WebSocketState.Open) return;

            byte[] bytes = Encoding.UTF8.GetBytes(jsonPayload);
            await webSocket.SendAsync(
                new ArraySegment<byte>(bytes),
                WebSocketMessageType.Text,
                true,
                cancellationTokenSource.Token
            );
        }

        public void DisconnectWebSocket()
        {
            try
            {
                cancellationTokenSource?.Cancel();
                if (webSocket != null && webSocket.State == WebSocketState.Open)
                {
                    webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Shutdown", CancellationToken.None);
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[NetworkClient] Error closing WebSocket: {ex.Message}");
            }
        }

        #endregion

        #region REST Endpoints

        public async Task<string> PostJsonAsync(string endpoint, string jsonPayload)
        {
            string url = $"{apiBaseUrl}/{endpoint.TrimStart('/')}";
            using (UnityWebRequest req = new UnityWebRequest(url, "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonPayload);
                req.uploadHandler = new UploadHandlerRaw(bodyRaw);
                req.downloadHandler = new DownloadHandlerBuffer();
                req.SetRequestHeader("Content-Type", "application/json");

                var operation = req.SendWebRequest();
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (req.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"[NetworkClient] POST {url} Error ({req.responseCode}): {req.error}");
                    throw new Exception($"HTTP Error: {req.error} - {req.downloadHandler.text}");
                }

                return req.downloadHandler.text;
            }
        }

        public async Task<string> GetJsonAsync(string endpoint)
        {
            string url = $"{apiBaseUrl}/{endpoint.TrimStart('/')}";
            using (UnityWebRequest req = UnityWebRequest.Get(url))
            {
                var operation = req.SendWebRequest();
                while (!operation.isDone)
                {
                    await Task.Yield();
                }

                if (req.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"[NetworkClient] GET {url} Error: {req.error}");
                    throw new Exception($"HTTP Error: {req.error}");
                }

                return req.downloadHandler.text;
            }
        }

        #endregion
    }
}
