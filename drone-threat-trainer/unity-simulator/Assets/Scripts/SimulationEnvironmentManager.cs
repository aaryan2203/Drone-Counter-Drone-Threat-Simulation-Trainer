using System;
using UnityEngine;

namespace DroneThreatTrainer.Simulation
{
    /// <summary>
    /// Adjusts dynamic lighting, atmospheric fog, and sky conditions to simulate
    /// different training environments (Urban, Rural, Industrial) and visibility tiers (Day, Night, Fog).
    /// </summary>
    public class SimulationEnvironmentManager : MonoBehaviour
    {
        [Header("Lighting References")]
        [SerializeField] private Light sunLight;
        [SerializeField] private Material daySkybox;
        [SerializeField] private Material nightSkybox;

        public void ApplyEnvironmentSettings(string environment, string lighting, string visibility)
        {
            ApplyLighting(lighting);
            ApplyVisibility(visibility);
            Debug.Log($"[EnvironmentManager] Configured Environment: {environment} | Lighting: {lighting} | Visibility: {visibility}");
        }

        private void ApplyLighting(string lighting)
        {
            if (sunLight == null)
            {
                sunLight = RenderSettings.sun;
                if (sunLight == null)
                {
                    GameObject lightObj = GameObject.Find("Directional Light");
                    if (lightObj != null) sunLight = lightObj.GetComponent<Light>();
                }
            }

            switch (lighting.ToLower())
            {
                case "night":
                    if (sunLight != null)
                    {
                        sunLight.intensity = 0.08f;
                        sunLight.color = new Color(0.3f, 0.4f, 0.6f);
                        sunLight.transform.rotation = Quaternion.Euler(15f, -30f, 0f);
                    }
                    RenderSettings.ambientLight = new Color(0.04f, 0.05f, 0.08f);
                    if (nightSkybox != null) RenderSettings.skybox = nightSkybox;
                    break;

                case "low_light":
                    if (sunLight != null)
                    {
                        sunLight.intensity = 0.4f;
                        sunLight.color = new Color(0.85f, 0.55f, 0.35f);
                        sunLight.transform.rotation = Quaternion.Euler(10f, -40f, 0f);
                    }
                    RenderSettings.ambientLight = new Color(0.18f, 0.16f, 0.18f);
                    break;

                case "day":
                default:
                    if (sunLight != null)
                    {
                        sunLight.intensity = 1.2f;
                        sunLight.color = Color.white;
                        sunLight.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
                    }
                    RenderSettings.ambientLight = new Color(0.4f, 0.4f, 0.45f);
                    if (daySkybox != null) RenderSettings.skybox = daySkybox;
                    break;
            }
        }

        private void ApplyVisibility(string visibility)
        {
            switch (visibility.ToLower())
            {
                case "fog":
                    RenderSettings.fog = true;
                    RenderSettings.fogMode = FogMode.ExponentialSquared;
                    RenderSettings.fogDensity = 0.025f;
                    RenderSettings.fogColor = new Color(0.6f, 0.65f, 0.7f);
                    break;

                case "reduced":
                    RenderSettings.fog = true;
                    RenderSettings.fogMode = FogMode.Exponential;
                    RenderSettings.fogDensity = 0.045f;
                    RenderSettings.fogColor = new Color(0.3f, 0.35f, 0.4f);
                    break;

                case "clear":
                default:
                    RenderSettings.fog = false;
                    break;
            }
        }
    }
}
