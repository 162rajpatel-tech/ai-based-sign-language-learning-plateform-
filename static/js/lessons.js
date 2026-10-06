/**
 * Lesson Catalog & Anatomical Sign Reference Manager.
 * Handles lesson selection, anatomical SVG generation, and finger checklist status.
 */

class LessonManager {
    constructor() {
        this.lessons = [];
        this.catalog = {};
        this.currentSign = 'A';
    }

    async loadLessons() {
        try {
            const res = await fetch('/api/lessons');
            const data = await res.json();
            this.lessons = data.lessons || [];
            this.catalog = data.catalog || {};
            return true;
        } catch (err) {
            console.error('Failed to load lessons:', err);
            return false;
        }
    }

    getSignData(code) {
        return this.catalog[code] || {
            code: code,
            name: `Letter ${code}`,
            category: 'alphabet',
            difficulty: 'Beginner',
            description: 'Perform the corresponding American Sign Language posture.',
            hints: ['Position your hand clearly facing the camera.'],
            finger_rules: {}
        };
    }

    renderSignSVG(code) {
        // High-definition SVG representations of ASL Meaningful Words & Expressions
        const svgTemplates = {
            'HELLO': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Open flat hand salute -->
                    <rect x="52" y="65" width="56" height="50" rx="12" fill="#1e293b" stroke="#94a3b8" stroke-width="2"/>
                    <rect x="55" y="24" width="10" height="52" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="67" y="18" width="10" height="58" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="79" y="20" width="10" height="56" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="91" y="28" width="10" height="48" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Motion wave ripples -->
                    <path d="M 115 35 Q 125 45 115 55" fill="none" stroke="#00f2fe" stroke-width="2" stroke-linecap="round"/>
                    <path d="M 122 28 Q 135 45 122 62" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round"/>
                    <text x="80" y="142" font-size="13" font-weight="900" fill="#00f2fe" text-anchor="middle">HELLO (GREETING)</text>
                </svg>`,

            'THANK_YOU': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#10b981" stroke-width="2"/>
                    <!-- Hand moving from chin outward -->
                    <rect x="50" y="72" width="60" height="45" rx="12" fill="#1e293b" stroke="#94a3b8" stroke-width="2"/>
                    <rect x="54" y="32" width="11" height="50" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <rect x="67" y="28" width="11" height="54" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <rect x="80" y="30" width="11" height="52" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <rect x="93" y="36" width="11" height="46" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <!-- Gratitude heart glow -->
                    <path d="M 38 45 C 38 35, 26 35, 26 45 C 26 53, 38 60, 38 60 C 38 60, 50 53, 50 45 C 50 35, 38 35, 38 45 Z" fill="#f43f5e" opacity="0.85"/>
                    <text x="80" y="142" font-size="13" font-weight="900" fill="#34d399" text-anchor="middle">THANK YOU</text>
                </svg>`,

            'YES': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Nodding S-Fist -->
                    <rect x="50" y="55" width="58" height="58" rx="16" fill="#334155" stroke="#94a3b8" stroke-width="3"/>
                    <path d="M 45 80 C 45 68, 75 66, 85 75" fill="none" stroke="#38bdf8" stroke-width="6" stroke-linecap="round"/>
                    <!-- Nod arrows -->
                    <path d="M 120 65 L 120 95 M 115 90 L 120 95 L 125 90" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#10b981" text-anchor="middle">YES (NOD)</text>
                </svg>`,

            'NO': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#f43f5e" stroke-width="2"/>
                    <!-- Index and Middle snapping down to thumb -->
                    <rect x="52" y="70" width="55" height="50" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <path d="M 52 35 C 55 55, 68 70, 75 75" fill="none" stroke="#fb7185" stroke-width="8" stroke-linecap="round"/>
                    <path d="M 66 35 C 68 55, 75 70, 78 75" fill="none" stroke="#fb7185" stroke-width="8" stroke-linecap="round"/>
                    <!-- Snap burst -->
                    <circle cx="80" cy="78" r="8" fill="#f43f5e" opacity="0.7"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#fb7185" text-anchor="middle">NO (SNAP)</text>
                </svg>`,

            'PLEASE': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#8b5cf6" stroke-width="2"/>
                    <rect x="50" y="65" width="60" height="50" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <rect x="54" y="25" width="11" height="50" rx="5" fill="#c084fc" stroke="#8b5cf6" stroke-width="2"/>
                    <rect x="67" y="20" width="11" height="55" rx="5" fill="#c084fc" stroke="#8b5cf6" stroke-width="2"/>
                    <rect x="80" y="22" width="11" height="53" rx="5" fill="#c084fc" stroke="#8b5cf6" stroke-width="2"/>
                    <rect x="93" y="28" width="11" height="47" rx="5" fill="#c084fc" stroke="#8b5cf6" stroke-width="2"/>
                    <!-- Chest circle motion -->
                    <ellipse cx="80" cy="75" rx="46" ry="46" fill="none" stroke="#a855f7" stroke-width="2" stroke-dasharray="6 6"/>
                    <text x="80" y="142" font-size="13" font-weight="900" fill="#c084fc" text-anchor="middle">PLEASE</text>
                </svg>`,

            'SORRY': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#f59e0b" stroke-width="2"/>
                    <rect x="50" y="55" width="58" height="58" rx="16" fill="#334155" stroke="#94a3b8" stroke-width="3"/>
                    <path d="M 45 80 C 45 68, 75 66, 85 75" fill="none" stroke="#fbbf24" stroke-width="6" stroke-linecap="round"/>
                    <!-- Rubbing chest circle -->
                    <circle cx="80" cy="80" r="48" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 5"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#fbbf24" text-anchor="middle">SORRY</text>
                </svg>`,

            'HELP': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Supporting base hand -->
                    <rect x="35" y="100" width="90" height="14" rx="6" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Lifted thumbs up fist -->
                    <rect x="52" y="60" width="54" height="42" rx="10" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <path d="M 46 80 C 44 65, 48 40, 56 32 C 62 26, 68 30, 66 40 C 64 52, 60 70, 60 80 Z" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Lift arrow -->
                    <path d="M 80 48 L 80 25 M 72 32 L 80 24 L 88 32" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#38bdf8" text-anchor="middle">HELP</text>
                </svg>`,

            'I_LOVE_YOU': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#ec4899" stroke-width="2"/>
                    <rect x="52" y="68" width="52" height="48" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <!-- Thumb horizontal left -->
                    <line x1="58" y1="92" x2="24" y2="82" stroke="#ec4899" stroke-width="11" stroke-linecap="round"/>
                    <!-- Index vertical -->
                    <line x1="62" y1="70" x2="56" y2="22" stroke="#ec4899" stroke-width="11" stroke-linecap="round"/>
                    <!-- Pinky vertical right -->
                    <line x1="96" y1="72" x2="108" y2="30" stroke="#ec4899" stroke-width="10" stroke-linecap="round"/>
                    <!-- Love heart center -->
                    <path d="M 80 82 C 78 76, 70 76, 70 82 C 70 88, 80 94, 80 94 C 80 94, 90 88, 90 82 C 90 76, 82 76, 80 82 Z" fill="#f43f5e"/>
                    <text x="80" y="142" font-size="13" font-weight="900" fill="#ec4899" text-anchor="middle">I LOVE YOU (ILY)</text>
                </svg>`,

            'GOOD': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#10b981" stroke-width="2"/>
                    <rect x="50" y="65" width="60" height="50" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <rect x="54" y="25" width="11" height="50" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <rect x="67" y="20" width="11" height="55" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <rect x="80" y="22" width="11" height="53" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <rect x="93" y="28" width="11" height="47" rx="5" fill="#34d399" stroke="#10b981" stroke-width="2"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#34d399" text-anchor="middle">GOOD</text>
                </svg>`,

            'STOP': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#f43f5e" stroke-width="2"/>
                    <!-- Flat vertical chopping hand -->
                    <rect x="52" y="65" width="56" height="48" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <rect x="55" y="22" width="10" height="52" rx="5" fill="#f43f5e" stroke="#fb7185" stroke-width="2"/>
                    <rect x="67" y="18" width="10" height="56" rx="5" fill="#f43f5e" stroke="#fb7185" stroke-width="2"/>
                    <rect x="79" y="20" width="10" height="54" rx="5" fill="#f43f5e" stroke="#fb7185" stroke-width="2"/>
                    <rect x="91" y="26" width="10" height="48" rx="5" fill="#f43f5e" stroke="#fb7185" stroke-width="2"/>
                    <!-- Chop line -->
                    <line x1="30" y1="108" x2="130" y2="108" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#f43f5e" text-anchor="middle">STOP (HALT)</text>
                </svg>`,

            'OK': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                    <!-- Thumb and index meeting in circle -->
                    <circle cx="58" cy="68" r="16" fill="none" stroke="#00f2fe" stroke-width="6"/>
                    <!-- 3 upright fingers -->
                    <rect x="76" y="22" width="11" height="52" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="89" y="26" width="11" height="48" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="102" y="34" width="11" height="40" rx="5" fill="#38bdf8" stroke="#00f2fe" stroke-width="2"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#00f2fe" text-anchor="middle">OK / ALRIGHT</text>
                </svg>`,

            'PEACE': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="55" y="70" width="50" height="48" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <!-- Index spread left -->
                    <line x1="68" y1="75" x2="48" y2="25" stroke="#38bdf8" stroke-width="12" stroke-linecap="round"/>
                    <!-- Middle spread right -->
                    <line x1="86" y1="75" x2="106" y2="25" stroke="#38bdf8" stroke-width="12" stroke-linecap="round"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#38bdf8" text-anchor="middle">PEACE</text>
                </svg>`,

            'CALL_ME': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>
                    <rect x="56" y="66" width="48" height="48" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <!-- Thumb left -->
                    <line x1="62" y1="92" x2="26" y2="80" stroke="#38bdf8" stroke-width="12" stroke-linecap="round"/>
                    <!-- Pinky right -->
                    <line x1="94" y1="74" x2="118" y2="44" stroke="#38bdf8" stroke-width="11" stroke-linecap="round"/>
                    <!-- Phone sound waves -->
                    <path d="M 125 35 Q 135 45 125 55" fill="none" stroke="#00f2fe" stroke-width="3" stroke-linecap="round"/>
                    <text x="80" y="142" font-size="13" font-weight="900" fill="#38bdf8" text-anchor="middle">CALL ME</text>
                </svg>`,

            'WATER': `
                <svg viewBox="0 0 160 160" class="sign-svg">
                    <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                    <rect x="52" y="65" width="56" height="50" rx="12" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                    <!-- W: 3 upright spread fingers -->
                    <line x1="60" y1="70" x2="48" y2="26" stroke="#38bdf8" stroke-width="10" stroke-linecap="round"/>
                    <line x1="78" y1="70" x2="78" y2="22" stroke="#38bdf8" stroke-width="10" stroke-linecap="round"/>
                    <line x1="96" y1="70" x2="108" y2="26" stroke="#38bdf8" stroke-width="10" stroke-linecap="round"/>
                    <!-- Water droplet -->
                    <path d="M 80 102 C 76 96, 72 90, 80 84 C 88 90, 84 96, 80 102 Z" fill="#00f2fe"/>
                    <text x="80" y="142" font-size="14" font-weight="900" fill="#00f2fe" text-anchor="middle">WATER</text>
                </svg>`
        };

        if (svgTemplates[code]) {
            return svgTemplates[code];
        }

        const cleanName = code.replace(/_/g, ' ');
        return `
            <svg viewBox="0 0 160 160" class="sign-svg">
                <circle cx="80" cy="80" r="72" fill="#0f172a" stroke="#00f2fe" stroke-width="2"/>
                <circle cx="80" cy="72" r="44" fill="#1e293b" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 4"/>
                <text x="80" y="80" font-size="20" font-weight="900" fill="#00f2fe" text-anchor="middle" font-family="'Outfit', sans-serif">${cleanName}</text>
                <text x="80" y="138" font-size="11" font-weight="bold" fill="#94a3b8" text-anchor="middle">MEANINGFUL WORD</text>
            </svg>
        `;
    }

    renderFingerChecklist(signCode, currentStates = {}) {
        const sign = this.getSignData(signCode);
        const rules = sign.finger_rules || {};

        const fingerKeys = [
            { key: 'thumb', label: 'Thumb', desc: rules.thumb || 'Positioned' },
            { key: 'index', label: 'Index Finger', desc: rules.index || 'Positioned' },
            { key: 'middle', label: 'Middle Finger', desc: rules.middle || 'Positioned' },
            { key: 'ring', label: 'Ring Finger', desc: rules.ring || 'Positioned' },
            { key: 'pinky', label: 'Pinky Finger', desc: rules.pinky || 'Positioned' }
        ];

        return fingerKeys.map(f => {
            const liveState = currentStates[f.key];
            let badgeClass = 'status-pending';
            let icon = '•';

            if (liveState) {
                const targetDesc = (f.desc || '').toLowerCase();
                if (targetDesc.includes(liveState) || (liveState === 'extended' && targetDesc.includes('straight'))) {
                    badgeClass = 'status-success';
                    icon = '✓';
                } else {
                    badgeClass = 'status-adjust';
                    icon = '⚠';
                }
            }

            return `
                <div class="finger-item ${badgeClass}">
                    <div class="finger-info">
                        <span class="finger-name">${f.label}</span>
                        <span class="finger-rule">${f.desc.replace(/_/g, ' ')}</span>
                    </div>
                    <div class="finger-indicator">${icon}</div>
                </div>
            `;
        }).join('');
    }

    renderRelatedTextDetails(code) {
        const sign = this.getSignData(code);
        const relatedWords = sign.related_words || [];
        const wordsHtml = relatedWords.length > 0 
            ? relatedWords.map(w => `<span class="vocab-tag">${w}</span>`).join('') 
            : `<span class="vocab-tag">${sign.code}</span>`;

        return `
            <div class="related-text-container">
                <div class="text-block">
                    <div class="text-label">🔤 Direct Text Translation</div>
                    <div class="translated-text-hero">"${sign.code.replace(/_/g, ' ')}"</div>
                </div>

                <div class="text-block">
                    <div class="text-label">📖 Sign Meaning & Context</div>
                    <p class="text-body">${sign.description || 'American Sign Language posture.'}</p>
                </div>

                <div class="text-block">
                    <div class="text-label">💬 ASL Conversational Usage</div>
                    <p class="text-body">${sign.usage || 'Standard manual alphabet fingerspelling in ASL.'}</p>
                </div>

                <div class="text-block">
                    <div class="text-label">📝 Example Sentence</div>
                    <div class="example-quote">${sign.example_sentence || `Fingerspelling word: '${sign.code}'`}</div>
                </div>

                ${sign.confusable_with ? `
                <div class="text-block confusion-alert">
                    <div class="text-label">⚠️ Easily Confused With</div>
                    <p class="text-body warning-text">${sign.confusable_with}</p>
                </div>` : ''}

                <div class="text-block">
                    <div class="text-label">🏷️ Related Vocabulary Words</div>
                    <div class="vocab-tags-list">
                        ${wordsHtml}
                    </div>
                </div>
            </div>
        `;
    }
}

window.LessonManager = LessonManager;

