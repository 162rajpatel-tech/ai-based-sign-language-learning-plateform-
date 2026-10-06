/**
 * Browser-side MediaPipe Hand Landmark Detector.
 * Runs the full 21-point hand landmark detection entirely in the browser
 * via WASM — no server-side OpenCV or MediaPipe required.
 *
 * Uses MediaPipe Tasks Vision JS (CDN loaded in index.html).
 */
class BrowserHandDetector {
    constructor() {
        this.handLandmarker = null;
        this.isReady = false;
        this.lastLandmarks = null;
        this._initPromise = null;
    }

    /**
     * Initializes the MediaPipe HandLandmarker with the .task model file.
     * The model is loaded from /static/models/ (served by Flask).
     */
    async init() {
        if (this._initPromise) return this._initPromise;
        this._initPromise = this._doInit();
        return this._initPromise;
    }

    async _doInit() {
        try {
            const { HandLandmarker, FilesetResolver } = await Promise.resolve(
                window.mpHandsReady
            );

            const vision = await FilesetResolver.forVisionTasks(
                'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
            );

            this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
                baseOptions: {
                    modelAssetPath: '/static/models/hand_landmarker.task',
                    delegate: 'GPU'
                },
                runningMode: 'VIDEO',
                numHands: 1,
                minHandDetectionConfidence: 0.5,
                minHandPresenceConfidence: 0.5,
                minTrackingConfidence: 0.5
            });

            this.isReady = true;
            console.log('[BrowserHandDetector] MediaPipe HandLandmarker ready (browser WASM).');
            return true;
        } catch (err) {
            // Fallback: try IMAGE mode (more compatible)
            try {
                console.warn('[BrowserHandDetector] GPU delegate failed, retrying with CPU...', err);
                const { HandLandmarker, FilesetResolver } = window.mpHandsReady
                    ? await Promise.resolve(window.mpHandsReady)
                    : mediapipe_tasks_vision;

                const vision = await FilesetResolver.forVisionTasks(
                    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
                );

                this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: '/static/models/hand_landmarker.task',
                        delegate: 'CPU'
                    },
                    runningMode: 'VIDEO',
                    numHands: 1,
                    minHandDetectionConfidence: 0.5,
                    minHandPresenceConfidence: 0.5,
                    minTrackingConfidence: 0.5
                });

                this.isReady = true;
                console.log('[BrowserHandDetector] MediaPipe HandLandmarker ready (CPU fallback).');
                return true;
            } catch (fallbackErr) {
                console.error('[BrowserHandDetector] Failed to initialize:', fallbackErr);
                this.isReady = false;
                return false;
            }
        }
    }

    /**
     * Detects hand landmarks from a video element frame.
     * Returns an array of 21 landmark objects {x, y, z} or null if no hand found.
     *
     * @param {HTMLVideoElement} videoElement
     * @returns {Array|null} Array of 21 {x,y,z} landmarks, or null
     */
    detectFromVideo(videoElement) {
        if (!this.isReady || !this.handLandmarker) return null;
        if (!videoElement || videoElement.readyState < 2) return null;

        try {
            const nowMs = performance.now();
            const results = this.handLandmarker.detectForVideo(videoElement, nowMs);

            if (results && results.landmarks && results.landmarks.length > 0) {
                // Convert MediaPipe NormalizedLandmark objects to plain {x,y,z} dicts
                const hand = results.landmarks[0];
                const landmarks = hand.map(lm => ({
                    x: lm.x,
                    y: lm.y,
                    z: lm.z
                }));
                this.lastLandmarks = landmarks;
                return landmarks;
            }

            this.lastLandmarks = null;
            return null;
        } catch (err) {
            // detectForVideo can throw if timestamp is not monotonically increasing
            this.lastLandmarks = null;
            return null;
        }
    }
}

// Expose globally
window.BrowserHandDetector = BrowserHandDetector;
