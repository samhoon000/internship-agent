import logger from './logger.js';

// Simple in-memory cache to throttle/debounce duplicate alerts (e.g. Redis reconnect loops)
const lastAlertTimes = new Map();
const THROTTLE_WINDOW_MS = 60 * 1000; // 1 minute throttle per title

/**
 * Sends a structured rich embed to the Discord Webhook URL.
 * Throttles duplicate alerts within a 1-minute window to avoid spam.
 * @param {string} title - The title of the alert embed.
 * @param {string} description - The description/message of the alert.
 * @param {'info' | 'warning' | 'error' | 'success'} status - The severity/status of the alert.
 */
export async function sendDiscordAlert(title, description, status = 'error') {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
  if (!webhookUrl) {
    logger.warn('[Alerting] DISCORD_WEBHOOK_URL is not set. Skipping Discord alert.', { title, description });
    return;
  }

  // Throttle check
  const now = Date.now();
  const lastTime = lastAlertTimes.get(title) || 0;
  if (now - lastTime < THROTTLE_WINDOW_MS) {
    logger.debug(`[Alerting] Throttling alert: "${title}" (last sent ${Math.round((now - lastTime) / 1000)}s ago)`);
    return;
  }
  lastAlertTimes.set(title, now);

  // Set colors based on status (decimal format for Discord embeds)
  let color = 16711680; // Default: Error Red (decimal for #ff0000)
  if (status === 'warning') color = 16776960; // Yellow (#ffff00)
  else if (status === 'success') color = 65280; // Green (#00ff00)
  else if (status === 'info') color = 255; // Blue (#0000ff)

  const payload = {
    embeds: [
      {
        title: title,
        description: description,
        color: color,
        timestamp: new Date().toISOString(),
        footer: {
          text: 'Internship Aggregator Production Monitor'
        }
      }
    ]
  };

  try {
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const text = await response.text();
      logger.error('[Alerting] Discord Webhook returned error response', { status: response.status, body: text });
    } else {
      logger.info('[Alerting] Alert successfully dispatched to Discord', { title });
    }
  } catch (err) {
    logger.error('[Alerting] Failed to dispatch Discord webhook alert', { error: err.message, stack: err.stack });
  }
}
