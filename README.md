# AI Edit Studio Android

This is an Android **client** for the included Python/Gradio video editor. It is NOT an offline or standalone video-rendering APK. Rendering, beat analysis, and MP4 creation run on a computer/server with FFmpeg. The app lets your phone upload video/music, type edit instructions, preview, and download results over Wi-Fi.

## 1. Run the editor on your computer

Install Python 3.11 or 3.12 and FFmpeg (including ffprobe). From this folder:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The editor listens on port 7860 on your computer's network interfaces. Keep the computer running. Allow inbound TCP port 7860 in your computer firewall **only on trusted private networks**. Do not expose the service to the public internet without authentication and HTTPS.

Find the computer's local IP address (e.g. `192.168.1.10`), then test `http://192.168.1.10:7860` in your Android phone's Chrome browser. Both devices must be on the same Wi-Fi network.

## 2. Build the APK using Android Studio

1. Install Android Studio with Android SDK 35 and JDK 17.
2. Open the `AI_Edit_Studio_Android` folder as a project.
3. Let Android Studio sync Gradle and download dependencies (internet required).
4. Select **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
5. Locate `app/build/outputs/apk/debug/app-debug.apk` and copy it to your phone.
6. Tap the APK on the phone; if prompted, allow installing from that source.
7. Launch **AI Edit Studio**, enter `http://YOUR_COMPUTER_IP:7860`, and tap **Connect**.

You can alternatively run `gradle assembleDebug` if you have Gradle installed; this project intentionally does not include a generated Gradle wrapper. Android Studio can sync it directly. For a release APK, configure a release signing key and build a signed APK via Android Studio.

## Limitations

- Rule-based prompt interpretation, not a connected LLM.
- Beat sync needs a music file; otherwise timed cuts are used.
- Video rendering requires a computer/server; APK is a mobile front end.
- Fade transitions are brief fades to/from black, not overlapping crossfades.
- Downloading from Gradio may require browser cookies/session; if downloads fail in the WebView, open the same server address in Chrome.
- The Android project has not been compiled or device-tested in this environment.
