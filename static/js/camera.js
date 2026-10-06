/**
 * Camera Stream Manager and Canvas Landmark Renderer.
 * Handles webcam capture, frame serialization, and smooth skeleton rendering.
 */
class CameraManager {
    constructor(videoElement, canvasElement) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.stream = null;
        this.isActive = false;
        this.isMirrored = true;

        // Offline canvas for frame downsampling (fast base64 extraction)
        this.captureCanvas = document.createElement('canvas');
        this.captureCanvas.width = 480;
        this.captureCanvas.height = 360;
        this.captureCtx = this.captureCanvas.getContext('2d');

        // Bone connection pairs matching MediaPipe hand topology
        this.connections = [
            [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
            [0, 5], [5, 6], [6, 7], [7, 8],       // Index
            [5, 9], [9, 10], [10, 11], [11, 12],  // Middle
            [9, 13], [13, 14], [14, 15], [15, 16],// Ring
            [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
            [0, 17]                               // Palm base
        ];
    }

    async startCamera() {
        try {
            const constraints = {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: "user"
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play();
                    this.resizeCanvas();
                    this.isActive = true;
                    resolve();
                };
            });

            window.addEventListener('resize', () => this.resizeCanvas());
            return true;
        } catch (err) {
            console.error("Camera access error:", err);
            return false;
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.isActive = false;
        this.clearCanvas();
    }

    resizeCanvas() {
        if (this.video.videoWidth) {
            this.canvas.width = this.video.clientWidth || this.video.videoWidth;
            this.canvas.height = this.video.clientHeight || this.video.videoY || this.video.videoHeight;
        }
    }

    clearCanvas() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    captureFrameBase64() {
        if (!this.isActive || this.video.readyState !== 4) return null;

        const cw = this.captureCanvas.width;
        const ch = this.captureCanvas.height;

        this.captureCtx.save();
        if (this.isMirrored) {
            this.captureCtx.translate(cw, 0);
            this.captureCtx.scale(-1, 1);
        }
        this.captureCtx.drawImage(this.video, 0, 0, cw, ch);
        this.captureCtx.restore();

        return this.captureCanvas.toDataURL('image/jpeg', 0.65);
    }

    drawSkeleton(landmarks, isMatch = false, confidence = 0.0) {
        this.clearCanvas();
        if (!landmarks || landmarks.length < 21) return;

        const w = this.canvas.width;
        const h = this.canvas.height;
        const ctx = this.ctx;

        // Convert normalized coords to screen pixels
        const pts = landmarks.map(lm => {
            let x = lm.x;
            if (this.isMirrored) {
                x = 1.0 - x;
            }
            return {
                x: x * w,
                y: lm.y * h
            };
        });

        // Determine theme colors based on matching state
        const boneColor = isMatch ? 'rgba(16, 185, 129, 0.95)' : 'rgba(0, 242, 254, 0.85)';
        const jointGlow = isMatch ? 'rgba(52, 211, 153, 0.6)' : 'rgba(59, 130, 246, 0.6)';
        const tipColor = isMatch ? '#10b981' : '#38bdf8';

        // Draw connections / bones
        ctx.save();
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.lineWidth = 4;
        ctx.strokeStyle = boneColor;
        ctx.shadowColor = boneColor;
        ctx.shadowBlur = 10;

        for (const [start, end] of this.connections) {
            if (pts[start] && pts[end]) {
                ctx.beginPath();
                ctx.moveTo(pts[start].x, pts[start].y);
                ctx.lineTo(pts[end].x, pts[end].y);
                ctx.stroke();
            }
        }
        ctx.restore();

        // Draw joints
        pts.forEach((pt, idx) => {
            const isFingertip = [4, 8, 12, 16, 20].includes(idx);
            const radius = isFingertip ? 7 : 4.5;

            // Outer glow
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, radius + 3, 0, 2 * Math.PI);
            ctx.fillStyle = jointGlow;
            ctx.fill();

            // Core point
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = isFingertip ? tipColor : '#ffffff';
            ctx.fill();

            // Border
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = '#ffffff';
            ctx.stroke();
        });

        // Draw palm target indicator
        if (pts[0] && pts[9]) {
            const palmCenterX = (pts[0].x + pts[9].x) / 2;
            const palmCenterY = (pts[0].y + pts[9].y) / 2;

            ctx.save();
            ctx.beginPath();
            ctx.arc(palmCenterX, palmCenterY, 14, 0, 2 * Math.PI);
            ctx.strokeStyle = isMatch ? 'rgba(16, 185, 129, 0.7)' : 'rgba(0, 242, 254, 0.5)';
            ctx.setLineDash([4, 4]);
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.restore();
        }
    }
}

window.CameraManager = CameraManager;
