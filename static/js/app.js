/**
 * Main Application Controller for AI-Based Sign Language Learning Platform.
 * Coordinates CV prediction loops, hold-to-confirm validation, sign-to-text transcription,
 * live educational context text, and Web Speech API synthesis.
 */

class AppController {
    constructor() {
        this.camera = null;
        this.lessons = new LessonManager();
        this.audio = window.soundEffects;

        // State
        this.currentSign = 'HELLO';
        this.currentMode = 'learn'; // 'learn', 'practice', 'quiz'
        this.activeCategory = 'word';
        this.isLoopRunning = false;
        this.isProcessingFrame = false;

        // Sign-to-Text Composer State
        this.composedSentence = "";
        this.lastPredictedWord = "";
        this.lastCommittedWord = "";
        this.lastCommittedTime = 0;

        // Hold-to-confirm verification timer
        this.holdProgress = 0.0;
        this.holdTargetSeconds = 1.3; // 1.3s sustained hold for meaningful words
        this.lastFrameTime = performance.now();
        this.successCooldown = false;

        // Quiz State
        this.quiz = {
            active: false,
            questions: [],
            currentIndex: 0,
            score: 0,
            timer: 10,
            interval: null
        };

        // Cache DOM elements
        this.dom = {};
    }

    async init() {
        this.cacheDom();
        this.bindEvents();

        // 1. Load lesson catalog
        await this.lessons.loadLessons();
        this.renderLessonCards();

        // 2. Select initial sign
        this.selectSign('HELLO');

        // 3. Initialize Camera
        this.camera = new CameraManager(this.dom.webcamVideo, this.dom.skeletonCanvas);
        const camOk = await this.camera.startCamera();
        if (camOk) {
            this.dom.cameraStatusText.textContent = "Camera Active • AI Landmarker Online";
            this.dom.cameraStatusBadge.classList.add("badge-active");
            this.startPredictionLoop();
        } else {
            this.dom.cameraStatusText.textContent = "Camera Access Blocked or Unavailable";
            this.dom.cameraStatusBadge.classList.add("badge-error");
        }

        // 4. Refresh progress and badges
        await this.refreshUserProgress();
    }

    cacheDom() {
        this.dom = {
            webcamVideo: document.getElementById('webcam-video'),
            skeletonCanvas: document.getElementById('skeleton-canvas'),
            cameraStatusText: document.getElementById('camera-status-text'),
            cameraStatusBadge: document.getElementById('camera-status-badge'),
            mirrorToggle: document.getElementById('mirror-toggle'),
            audioToggle: document.getElementById('audio-toggle'),

            // Live Subtitles & Sign-to-Text Bar
            liveSubtitleBar: document.getElementById('live-subtitle-bar'),
            liveSubtitleText: document.getElementById('live-subtitle-text'),
            liveSubtitleHint: document.getElementById('live-subtitle-hint'),

            // Sentence Composer
            composedTextBox: document.getElementById('composed-text-box'),
            toggleAutoAppend: document.getElementById('toggle-auto-append'),
            btnSpeakText: document.getElementById('btn-speak-text'),
            btnCommitSign: document.getElementById('btn-commit-sign'),
            btnAddSpace: document.getElementById('btn-add-space'),
            btnBackspace: document.getElementById('btn-backspace'),
            btnCopyText: document.getElementById('btn-copy-text'),
            btnClearText: document.getElementById('btn-clear-text'),

            // Text Related to Sign Given by User (Insights Panel)
            relatedTextContainer: document.getElementById('related-text-container'),
            detectedSignContextBadge: document.getElementById('detected-sign-context-badge'),

            // Sign Reference Studio
            targetSignCode: document.getElementById('target-sign-code'),
            targetSignTitle: document.getElementById('target-sign-title'),
            targetSignCategory: document.getElementById('target-sign-category'),
            targetSignDifficulty: document.getElementById('target-sign-difficulty'),
            targetSignDescription: document.getElementById('target-sign-description'),
            signSvgContainer: document.getElementById('sign-svg-container'),
            fingerChecklist: document.getElementById('finger-checklist'),
            hintsContainer: document.getElementById('hints-container'),
            funFactText: document.getElementById('fun-fact-text'),

            // Recognition HUD
            predictedSignBadge: document.getElementById('predicted-sign-badge'),
            confidenceMeterBar: document.getElementById('confidence-meter-bar'),
            confidenceValue: document.getElementById('confidence-value'),
            feedbackBanner: document.getElementById('feedback-banner'),
            feedbackMessage: document.getElementById('feedback-message'),
            holdProgressCircle: document.getElementById('hold-progress-circle'),
            holdPercentText: document.getElementById('hold-percent-text'),
            topPredictionsList: document.getElementById('top-predictions-list'),

            // Gamification & Header
            userXpText: document.getElementById('user-xp-text'),
            streakCountText: document.getElementById('streak-count-text'),
            masteryRateText: document.getElementById('mastery-rate-text'),
            badgesCountText: document.getElementById('badges-count-text'),

            // Lessons List
            lessonTabs: document.querySelectorAll('.category-tab'),
            lessonsGrid: document.getElementById('lessons-grid'),

            // Quiz & Modals
            quizModal: document.getElementById('quiz-modal'),
            quizTargetSign: document.getElementById('quiz-target-sign'),
            quizTimer: document.getElementById('quiz-timer'),
            quizScore: document.getElementById('quiz-score'),
            badgesModal: document.getElementById('badges-modal'),
            badgesGrid: document.getElementById('badges-grid'),

            // Mode Buttons
            modeBtns: document.querySelectorAll('.mode-btn')
        };
    }

    bindEvents() {
        // Category Tabs
        this.dom.lessonTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.dom.lessonTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.activeCategory = tab.dataset.category;
                this.renderLessonCards();
            });
        });

        // Mode switchers
        this.dom.modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.dom.modeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.setMode(btn.dataset.mode);
            });
        });

        // Video & Audio Controls
        if (this.dom.mirrorToggle) {
            this.dom.mirrorToggle.addEventListener('click', () => {
                if (this.camera) {
                    this.camera.isMirrored = !this.camera.isMirrored;
                    this.dom.mirrorToggle.classList.toggle('active', this.camera.isMirrored);
                    this.dom.webcamVideo.style.transform = this.camera.isMirrored ? 'scaleX(-1)' : 'scaleX(1)';
                }
            });
        }

        if (this.dom.audioToggle) {
            this.dom.audioToggle.addEventListener('click', () => {
                this.audio.enabled = !this.audio.enabled;
                this.dom.audioToggle.classList.toggle('active', this.audio.enabled);
            });
        }

        // Sentence Composer Controls
        if (this.dom.btnSpeakText) {
            this.dom.btnSpeakText.addEventListener('click', () => this.speakComposedText());
        }

        if (this.dom.btnCommitSign) {
            this.dom.btnCommitSign.addEventListener('click', () => {
                const word = (this.lastPredictedWord || this.currentSign).replace(/_/g, ' ');
                this.appendWordToComposer(word);
            });
        }

        if (this.dom.btnAddSpace) {
            this.dom.btnAddSpace.addEventListener('click', () => {
                this.composedSentence += " ";
                this.dom.composedTextBox.value = this.composedSentence;
            });
        }

        if (this.dom.btnBackspace) {
            this.dom.btnBackspace.addEventListener('click', () => {
                const words = this.composedSentence.trim().split(" ");
                words.pop();
                this.composedSentence = words.join(" ") + (words.length > 0 ? " " : "");
                this.dom.composedTextBox.value = this.composedSentence;
            });
        }

        if (this.dom.btnCopyText) {
            this.dom.btnCopyText.addEventListener('click', () => {
                if (!this.composedSentence) return;
                navigator.clipboard.writeText(this.composedSentence);
                alert("Copied translated text to clipboard: " + this.composedSentence);
            });
        }

        if (this.dom.btnClearText) {
            this.dom.btnClearText.addEventListener('click', () => {
                this.composedSentence = "";
                this.dom.composedTextBox.value = "";
            });
        }

        // Quiz buttons
        document.getElementById('start-quiz-btn')?.addEventListener('click', () => this.startQuiz());
        document.getElementById('close-quiz-btn')?.addEventListener('click', () => this.endQuiz());
        document.getElementById('open-badges-btn')?.addEventListener('click', () => this.openBadgesModal());
        document.getElementById('close-badges-btn')?.addEventListener('click', () => this.dom.badgesModal.classList.remove('open'));
        document.getElementById('next-sign-btn')?.addEventListener('click', () => this.goToNextSign());
    }

    setMode(mode) {
        this.currentMode = mode;
        if (mode === 'quiz') {
            this.startQuiz();
        }
    }

    selectSign(signCode) {
        this.currentSign = signCode;
        const sign = this.lessons.getSignData(signCode);

        // Update Reference Studio
        this.dom.targetSignCode.textContent = sign.code.replace(/_/g, ' ');
        this.dom.targetSignTitle.textContent = sign.name;
        this.dom.targetSignCategory.textContent = (sign.category || 'word').toUpperCase();
        this.dom.targetSignDifficulty.textContent = sign.difficulty || 'Beginner';
        this.dom.targetSignDescription.textContent = sign.description;
        this.dom.funFactText.textContent = sign.fun_fact || "Practice holding your posture steady for 1.3 seconds to confirm.";

        // Render SVG Vector Diagram
        this.dom.signSvgContainer.innerHTML = this.lessons.renderSignSVG(signCode);

        // Render Initial Checklist
        this.dom.fingerChecklist.innerHTML = this.lessons.renderFingerChecklist(signCode, {});

        // Render Related Text Insights Panel
        this.dom.relatedTextContainer.innerHTML = this.lessons.renderRelatedTextDetails(signCode);
        this.dom.detectedSignContextBadge.textContent = sign.code.replace(/_/g, ' ');

        // Hints
        this.renderHints(sign.hints || []);

        // Reset verification timer
        this.holdProgress = 0;
        this.updateHoldProgressBar(0);
        this.feedbackBanner('align', `Position your hand to sign: ${sign.code.replace(/_/g, ' ')}`);

        // Update active card styling
        document.querySelectorAll('.lesson-card').forEach(card => {
            card.classList.toggle('active', card.dataset.code === signCode);
        });
    }

    goToNextSign() {
        const words = this.lessons.lessons;
        const currentIndex = words.findIndex(l => l.sign_code === this.currentSign);
        if (currentIndex >= 0 && currentIndex < words.length - 1) {
            this.selectSign(words[currentIndex + 1].sign_code);
        } else if (words.length > 0) {
            this.selectSign(words[0].sign_code);
        }
    }

    renderHints(hintsList) {
        if (!hintsList || hintsList.length === 0) {
            this.dom.hintsContainer.innerHTML = `<div class="hint-item">No specific corrections needed. Keep hand steady!</div>`;
            return;
        }
        this.dom.hintsContainer.innerHTML = hintsList.map(h => `
            <div class="hint-item">
                <span class="hint-bullet">💡</span>
                <span>${h}</span>
            </div>
        `).join('');
    }

    renderLessonCards() {
        const list = this.lessons.lessons;
        this.dom.lessonsGrid.innerHTML = list.map(l => {
            const mastery = l.mastery_score || 0;
            const isCompleted = l.completed === 1;
            const isActive = l.sign_code === this.currentSign;
            const cleanTitle = l.sign_code.replace(/_/g, ' ');

            return `
                <div class="lesson-card ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}" data-code="${l.sign_code}">
                    <div class="card-header">
                        <span class="sign-pill">${cleanTitle}</span>
                        <span class="card-difficulty">${l.difficulty}</span>
                    </div>
                    <div class="card-title">${l.name}</div>
                    <div class="card-progress">
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width: ${mastery}%"></div>
                        </div>
                        <span class="progress-label">${mastery}%</span>
                    </div>
                </div>
            `;
        }).join('');

        // Bind clicks
        this.dom.lessonsGrid.querySelectorAll('.lesson-card').forEach(card => {
            card.addEventListener('click', () => {
                this.selectSign(card.dataset.code);
            });
        });
    }

    startPredictionLoop() {
        if (this.isLoopRunning) return;
        this.isLoopRunning = true;

        const loop = async (timestamp) => {
            if (!this.isLoopRunning) return;

            const deltaSeconds = (timestamp - this.lastFrameTime) / 1000;
            this.lastFrameTime = timestamp;

            if (!this.isProcessingFrame && this.camera && this.camera.isActive) {
                await this.processCurrentFrame(deltaSeconds);
            }

            requestAnimationFrame(loop);
        };

        requestAnimationFrame(loop);
    }

    async processCurrentFrame(deltaSeconds) {
        this.isProcessingFrame = true;

        try {
            const base64Image = this.camera.captureFrameBase64();
            if (!base64Image) {
                this.isProcessingFrame = false;
                return;
            }

            const target = this.quiz.active ? this.quiz.currentTarget : this.currentSign;
            const payload = {
                image: base64Image,
                target_sign: target
            };

            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                this.isProcessingFrame = false;
                return;
            }

            const data = await response.json();
            this.handlePredictionResponse(data, deltaSeconds);

        } catch (err) {
            console.error('Prediction loop error:', err);
        } finally {
            this.isProcessingFrame = false;
        }
    }

    handlePredictionResponse(data, deltaSeconds) {
        const { hand_detected, predicted_sign, confidence, is_match, landmarks, hints, finger_states, top_predictions, related_text } = data;

        // 1. Draw Skeleton on Canvas
        if (hand_detected && landmarks) {
            this.camera.drawSkeleton(landmarks, is_match, confidence);
        } else {
            this.camera.clearCanvas();
        }

        // 2. Update HUD
        if (!hand_detected) {
            this.dom.predictedSignBadge.textContent = "—";
            this.dom.predictedSignBadge.className = "prediction-badge badge-idle";
            this.dom.confidenceMeterBar.style.width = "0%";
            this.dom.confidenceValue.textContent = "0%";
            this.dom.liveSubtitleText.textContent = "—";
            this.dom.liveSubtitleHint.textContent = "Bring your hand into the camera frame";
            this.feedbackBanner('warning', 'Bring your hand into the camera frame');
            this.holdProgress = Math.max(0, this.holdProgress - deltaSeconds * 1.5);
            this.updateHoldProgressBar(this.holdProgress);
            return;
        }

        // Predicted Word & Confidence
        const cleanWord = (predicted_sign || "").replace(/_/g, ' ');
        this.lastPredictedWord = cleanWord;

        this.dom.predictedSignBadge.textContent = cleanWord || "?";
        const confPercent = Math.round((confidence || 0) * 100);
        this.dom.confidenceMeterBar.style.width = `${confPercent}%`;
        this.dom.confidenceValue.textContent = `${confPercent}%`;

        // Update Live Subtitle Bar (Real-Time Sign-to-Text)
        this.dom.liveSubtitleText.textContent = `"${cleanWord}"`;
        if (related_text && related_text.meaning) {
            this.dom.liveSubtitleHint.textContent = `Meaning: ${related_text.meaning}`;
        } else {
            this.dom.liveSubtitleHint.textContent = "Meaningful gesture recognized in real-time";
        }

        // Dynamically update the Text Related to Sign Given by User panel
        if (predicted_sign && this.dom.detectedSignContextBadge.textContent !== cleanWord) {
            this.dom.detectedSignContextBadge.textContent = cleanWord;
            this.dom.relatedTextContainer.innerHTML = this.lessons.renderRelatedTextDetails(predicted_sign);
        }

        // Update Top Predictions list
        this.renderTopPredictions(top_predictions);

        // Update Live Finger State Checklist
        const targetSign = this.quiz.active ? this.quiz.currentTarget : this.currentSign;
        this.dom.fingerChecklist.innerHTML = this.lessons.renderFingerChecklist(targetSign, finger_states || {});

        // 3. Evaluate Match & Sustained Hold Verification
        if (is_match && confidence >= 0.55) {
            this.dom.predictedSignBadge.className = "prediction-badge badge-match";
            this.feedbackBanner('success', `Meaningful Word Detected: ${cleanWord} (${confPercent}%)`);

            if (!this.successCooldown) {
                this.holdProgress += deltaSeconds / this.holdTargetSeconds;
                this.updateHoldProgressBar(this.holdProgress);

                if (this.holdProgress >= 1.0) {
                    this.onSignSucceeded(targetSign, confidence);
                }
            }
        } else {
            this.dom.predictedSignBadge.className = "prediction-badge badge-adjust";
            this.holdProgress = Math.max(0, this.holdProgress - deltaSeconds * 1.8);
            this.updateHoldProgressBar(this.holdProgress);

            if (hints && hints.length > 0) {
                this.feedbackBanner('adjust', hints[0]);
                this.renderHints(hints);
            } else {
                this.feedbackBanner('adjust', `Adjusting towards word: ${targetSign.replace(/_/g, ' ')}`);
            }
        }
    }

    renderTopPredictions(topList) {
        if (!topList || topList.length === 0) return;
        this.dom.topPredictionsList.innerHTML = topList.map(item => `
            <div class="top-pred-item" style="padding: 4px 8px; background: rgba(15,23,42,0.6); border-radius: 6px;">
                <span class="pred-label" style="font-weight: bold; color: #38bdf8;">${item.sign.replace(/_/g, ' ')}</span>
                <span class="pred-conf" style="color: #94a3b8; margin-left: 4px;">${Math.round(item.confidence * 100)}%</span>
            </div>
        `).join('');
    }

    updateHoldProgressBar(progress01) {
        const clamped = Math.min(1.0, Math.max(0.0, progress01));
        const percent = Math.round(clamped * 100);
        this.dom.holdPercentText.textContent = `${percent}%`;

        // SVG circular dash offset
        const circumference = 264;
        const offset = circumference - (circumference * clamped);
        this.dom.holdProgressCircle.style.strokeDashoffset = offset;
    }

    feedbackBanner(type, message) {
        this.dom.feedbackBanner.className = `feedback-banner feedback-${type}`;
        this.dom.feedbackMessage.textContent = message;
    }

    appendWordToComposer(word) {
        if (!word) return;
        const now = performance.now();
        // Prevent accidental duplicate spam within 1.5 seconds
        if (word === this.lastCommittedWord && (now - this.lastCommittedTime) < 1500) {
            return;
        }

        this.lastCommittedWord = word;
        this.lastCommittedTime = now;

        if (this.composedSentence && !this.composedSentence.endsWith(" ")) {
            this.composedSentence += " ";
        }
        this.composedSentence += word;
        this.dom.composedTextBox.value = this.composedSentence;
    }

    speakComposedText() {
        const textToSpeak = this.composedSentence.trim() || this.lastPredictedWord || this.currentSign.replace(/_/g, ' ');
        if ('speechSynthesis' in window && textToSpeak) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(textToSpeak);
            utterance.rate = 0.95;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }
    }

    async onSignSucceeded(signCode, confidence) {
        this.successCooldown = true;
        const cleanWord = signCode.replace(/_/g, ' ');
        this.audio.playSuccessChime();

        this.feedbackBanner('celebrate', `🎉 EXCELLENT! Word Verified: "${cleanWord}"`);
        this.showFloatingXP("+40 XP");

        // Automatically append to sentence composer if enabled
        if (this.dom.toggleAutoAppend && this.dom.toggleAutoAppend.checked) {
            this.appendWordToComposer(cleanWord);
            // Optionally speak word
            if ('speechSynthesis' in window) {
                const utter = new SpeechSynthesisUtterance(cleanWord);
                utter.rate = 1.0;
                window.speechSynthesis.speak(utter);
            }
        }

        // Record to backend database
        try {
            const res = await fetch('/api/progress/attempt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sign_code: signCode,
                    predicted_sign: signCode,
                    confidence: confidence,
                    is_correct: true,
                    duration_ms: Math.round(this.holdTargetSeconds * 1000)
                })
            });

            if (res.ok) {
                const data = await res.json();
                this.updateGamificationHeader(data.user_stats);

                // Show badge toast if new badge unlocked
                if (data.new_badges && data.new_badges.length > 0) {
                    this.audio.playFanfare();
                    this.showBadgeNotification(data.new_badges[0]);
                }
            }
        } catch (err) {
            console.error('Failed to log attempt:', err);
        }

        // Quiz mode branch
        if (this.quiz.active) {
            this.quiz.score += 15;
            this.dom.quizScore.textContent = this.quiz.score;
            setTimeout(() => this.nextQuizQuestion(), 1200);
            return;
        }

        // Reset verification cooldown after celebration
        setTimeout(() => {
            this.holdProgress = 0;
            this.updateHoldProgressBar(0);
            this.successCooldown = false;
        }, 1600);
    }

    showFloatingXP(text) {
        const el = document.createElement('div');
        el.className = 'floating-xp-toast';
        el.textContent = text;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 1500);
    }

    showBadgeNotification(badge) {
        const toast = document.createElement('div');
        toast.className = 'badge-unlock-toast';
        toast.innerHTML = `
            <div class="toast-icon">${badge.icon}</div>
            <div class="toast-content">
                <h4>Achievement Unlocked!</h4>
                <p>${badge.title}: ${badge.desc}</p>
            </div>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    async refreshUserProgress() {
        try {
            const res = await fetch('/api/progress');
            if (res.ok) {
                const data = await res.json();
                this.updateGamificationHeader(data);
            }
        } catch (err) {
            console.error('Failed to refresh user progress:', err);
        }
    }

    updateGamificationHeader(userStats) {
        if (!userStats || !userStats.user) return;
        this.dom.userXpText.textContent = `${userStats.user.total_xp} XP`;
        this.dom.streakCountText.textContent = `${userStats.user.streak_days} Day Streak`;
        this.dom.masteryRateText.textContent = `${userStats.stats.completion_rate}%`;
        this.dom.badgesCountText.textContent = `${userStats.badges.length}`;

        // Re-render lesson card mastery badges
        if (userStats.progress) {
            userStats.progress.forEach(p => {
                const lesson = this.lessons.lessons.find(l => l.sign_code === p.sign_code);
                if (lesson) {
                    lesson.mastery_score = p.mastery_score;
                    lesson.completed = p.completed;
                }
            });
            this.renderLessonCards();
        }
    }

    // --- Quiz & Challenge Mode for Meaningful Words ---
    startQuiz() {
        this.quiz.active = true;
        this.quiz.score = 0;
        this.quiz.currentIndex = 0;
        
        // Pick 6 random meaningful words
        const available = Object.keys(this.lessons.catalog);
        this.quiz.questions = [...available].sort(() => 0.5 - Math.random()).slice(0, 6);

        this.dom.quizModal.classList.add('open');
        this.dom.quizScore.textContent = '0';
        this.nextQuizQuestion();
    }

    nextQuizQuestion() {
        if (this.quiz.currentIndex >= this.quiz.questions.length) {
            this.finishQuiz();
            return;
        }

        const target = this.quiz.questions[this.quiz.currentIndex];
        this.quiz.currentTarget = target;
        this.quiz.currentIndex += 1;

        this.dom.quizTargetSign.textContent = target.replace(/_/g, ' ');
        this.selectSign(target);

        // Reset question timer (10 seconds)
        clearInterval(this.quiz.interval);
        this.quiz.timer = 10;
        this.dom.quizTimer.textContent = `${this.quiz.timer}s`;

        this.quiz.interval = setInterval(() => {
            this.quiz.timer -= 1;
            this.dom.quizTimer.textContent = `${this.quiz.timer}s`;
            if (this.quiz.timer <= 0) {
                clearInterval(this.quiz.interval);
                this.audio.playTryAgainCue();
                this.nextQuizQuestion();
            }
        }, 1000);
    }

    finishQuiz() {
        clearInterval(this.quiz.interval);
        this.quiz.active = false;
        this.audio.playFanfare();
        alert(`🏆 Quiz Complete! You scored ${this.quiz.score} points practicing meaningful ASL words.`);
        this.dom.quizModal.classList.remove('open');
        this.setMode('learn');
    }

    endQuiz() {
        clearInterval(this.quiz.interval);
        this.quiz.active = false;
        this.dom.quizModal.classList.remove('open');
        this.setMode('learn');
    }

    async openBadgesModal() {
        const res = await fetch('/api/progress');
        const data = await res.json();
        const badges = data.badges || [];

        this.dom.badgesGrid.innerHTML = badges.length > 0 ? badges.map(b => `
            <div class="badge-item unlocked">
                <div class="badge-icon">${b.icon}</div>
                <div class="badge-title">${b.badge_title}</div>
                <div class="badge-desc">${b.badge_desc}</div>
                <div class="badge-date">Unlocked: ${b.unlocked_at.slice(0, 10)}</div>
            </div>
        `).join('') : '<div class="no-badges">No badges yet! Complete practice lessons to unlock achievements.</div>';

        this.dom.badgesModal.classList.add('open');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new AppController();
    window.app.init();
});
