document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    // ELEMENTS
    // ============================================================

    const topic =
        document.getElementById("topic");

    const customTopicContainer =
        document.getElementById("custom-topic-container");

    const customTopic =
        document.getElementById("custom-topic");

    const upload =
        document.getElementById("upload");

    const privacyContainer =
        document.getElementById("privacy-container");

    const language =
        document.getElementById("language");

    const tone =
        document.getElementById("tone");

    const voice =
        document.getElementById("voice");

    const stories =
        document.getElementById("stories");

    const duration =
        document.getElementById("duration");

    const visual =
        document.getElementById("visual");

    const privacy =
        document.getElementById("privacy");

    const previewButton =
        document.getElementById("preview-button");

    const generateButton =
        document.getElementById("generate-button");

    const previewCard =
        document.getElementById("preview-card");

    const previewContent =
        document.getElementById("preview-content");

    const message =
        document.getElementById("message");


    // ============================================================
    // CUSTOM TOPIC
    // ============================================================

    function updateTopic() {

        if (topic.value === "custom") {

            customTopicContainer
                .classList
                .remove("hidden");

        } else {

            customTopicContainer
                .classList
                .add("hidden");

            customTopic.value = "";
        }
    }


    topic.addEventListener(
        "change",
        updateTopic
    );


    // ============================================================
    // YOUTUBE PRIVACY
    // ============================================================

    function updatePrivacy() {

        if (upload.checked) {

            privacyContainer
                .classList
                .remove("hidden");

        } else {

            privacyContainer
                .classList
                .add("hidden");
        }
    }


    upload.addEventListener(
        "change",
        updatePrivacy
    );


    // ============================================================
    // VOICE CONFIGURATION
    // ============================================================

    const voiceGroups = {

        english: [
            {
                value:
                    "en-US-AndrewNeural",

                label:
                    "Andrew — Warm & Confident"
            },

            {
                value:
                    "en-US-ChristopherNeural",

                label:
                    "Christopher — Professional"
            },

            {
                value:
                    "en-US-BrianNeural",

                label:
                    "Brian — Casual & Approachable"
            },

            {
                value:
                    "en-US-GuyNeural",

                label:
                    "Guy — News & Passion"
            },

            {
                value:
                    "en-US-JennyNeural",

                label:
                    "Jenny — Friendly"
            },

            {
                value:
                    "en-US-EmmaNeural",

                label:
                    "Emma — Cheerful & Clear"
            }
        ],


        hindi: [
            {
                value:
                    "hi-IN-MadhurNeural",

                label:
                    "Madhur — Hindi Male"
            },

            {
                value:
                    "hi-IN-SwaraNeural",

                label:
                    "Swara — Hindi Female"
            }
        ],


        hinglish: [
            {
                value:
                    "en-IN-PrabhatNeural",

                label:
                    "Prabhat — Indian Male"
            },

            {
                value:
                    "en-IN-NeerjaNeural",

                label:
                    "Neerja — Indian Female"
            }
        ]
    };


    // ============================================================
    // UPDATE VOICES BASED ON LANGUAGE
    // ============================================================

    function updateVoicesForLanguage() {

        const selectedLanguage =
            language.value;

        const voices =
            voiceGroups[
                selectedLanguage
            ]
            || voiceGroups.english;


        voice.innerHTML = "";


        voices.forEach(
            item => {

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    item.value;

                option.textContent =
                    item.label;

                voice.appendChild(
                    option
                );
            }
        );


        // Select first valid voice
        if (voices.length > 0) {

            voice.value =
                voices[0].value;
        }
    }


    language.addEventListener(
        "change",
        updateVoicesForLanguage
    );


    // ============================================================
    // SETTINGS
    // ============================================================

    function getSettings() {

        let selectedTopic =
            topic.value;


        if (
            selectedTopic === "custom"
        ) {

            selectedTopic =
                customTopic.value.trim();

            if (!selectedTopic) {

                selectedTopic =
                    "Custom Topic";
            }
        }


        return {

            topic:
                selectedTopic,

            language:
                language.value,

            tone:
                tone.value,

            voice:
                voice.value,

            stories:
                Number(
                    stories.value
                ),

            duration:
                Number(
                    duration.value
                ),

            visual:
                visual.value,

            upload:
                upload.checked,

            privacy:
                privacy.value
        };
    }


    // ============================================================
    // PREVIEW ITEM
    // ============================================================

    function addPreviewItem(
        label,
        value
    ) {

        const item =
            document.createElement(
                "div"
            );

        item.className =
            "preview-item";


        const labelElement =
            document.createElement(
                "span"
            );

        labelElement.className =
            "preview-label";

        labelElement.textContent =
            label;


        const valueElement =
            document.createElement(
                "span"
            );

        valueElement.className =
            "preview-value";

        valueElement.textContent =
            value;


        item.appendChild(
            labelElement
        );

        item.appendChild(
            valueElement
        );


        previewContent.appendChild(
            item
        );
    }


    // ============================================================
    // PREVIEW
    // ============================================================

    previewButton.addEventListener(
        "click",
        () => {

            const settings =
                getSettings();


            previewContent.innerHTML =
                "";


            addPreviewItem(
                "Topic",
                settings.topic
            );


            addPreviewItem(
                "Audio Language",
                getLanguageName(
                    settings.language
                )
            );


            addPreviewItem(
                "Tone",
                getToneName(
                    settings.tone
                )
            );


            addPreviewItem(
                "Voice",
                getVoiceName(
                    settings.voice
                )
            );


            addPreviewItem(
                "Stories",
                `Top ${settings.stories}`
            );


            addPreviewItem(
                "Duration",
                `${settings.duration} seconds`
            );


            addPreviewItem(
                "Visual",
                getVisualName(
                    settings.visual
                )
            );


            addPreviewItem(
                "YouTube Upload",
                settings.upload
                    ? "Enabled"
                    : "Disabled"
            );


            if (settings.upload) {

                addPreviewItem(
                    "Privacy",
                    getPrivacyName(
                        settings.privacy
                    )
                );
            }


            previewCard
                .classList
                .remove("hidden");


            previewCard.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });
        }
    );


    // ============================================================
    // GENERATE VIDEO
    // ============================================================

    generateButton.addEventListener(
        "click",
        async () => {

            const settings =
                getSettings();


            // ----------------------------------------------------
            // BUTTON STATE
            // ----------------------------------------------------

            generateButton.disabled =
                true;


            const originalText =
                generateButton.textContent;


            generateButton.textContent =
                "⏳ Generating...";


            message
                .classList
                .remove("hidden");


            message.textContent =
                "Starting AI Shorts pipeline...";


            previewCard
                .classList
                .add("hidden");


            try {

                console.log(
                    "AI Shorts settings:",
                    settings
                );


                // ------------------------------------------------
                // API REQUEST
                // ------------------------------------------------

                const response =
                    await fetch(
                        "/api/generate",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(
                                    settings
                                )
                        }
                    );


                console.log(
                    "API status:",
                    response.status
                );


                // ------------------------------------------------
                // API RESPONSE
                // ------------------------------------------------

                const data =
                    await response.json();


                console.log(
                    "API response:",
                    data
                );


                if (
                    !response.ok
                    || !data.success
                ) {

                    throw new Error(
                        data.error
                        || "Video generation failed."
                    );
                }


                // ------------------------------------------------
                // RESULT
                // ------------------------------------------------

                const result =
                    data.result
                    || {};


                let successMessage =
                    "✅ Video generated successfully.";


                if (
                    result.youtube_uploaded
                    && result.youtube_url
                ) {

                    successMessage +=
                        `\n\nYouTube:\n${result.youtube_url}`;

                } else {

                    successMessage +=
                        `\n\nVideo:\n${result.video_file || ""}`;
                }


                message.textContent =
                    successMessage;


                // ------------------------------------------------
                // RESULT PREVIEW
                // ------------------------------------------------

                previewContent.innerHTML =
                    "";


                addPreviewItem(
                    "Status",
                    "Completed"
                );


                addPreviewItem(
                    "Title",
                    result.title
                    || "AI News Short"
                );


                addPreviewItem(
                    "Language",
                    getLanguageName(
                        result.language
                        || settings.language
                    )
                );


                addPreviewItem(
                    "Tone",
                    getToneName(
                        result.tone
                        || settings.tone
                    )
                );


                addPreviewItem(
                    "Voice",
                    getVoiceName(
                        result.voice
                        || settings.voice
                    )
                );


                addPreviewItem(
                    "Video",
                    result.video_file
                    || "Generated"
                );


                if (
                    result.youtube_uploaded
                ) {

                    addPreviewItem(
                        "YouTube",
                        result.youtube_url
                        || "Uploaded"
                    );


                    addPreviewItem(
                        "Privacy",
                        getPrivacyName(
                            result.privacy
                            || settings.privacy
                        )
                    );

                } else {

                    addPreviewItem(
                        "YouTube",
                        "Upload skipped"
                    );
                }


                previewCard
                    .classList
                    .remove("hidden");


                previewCard.scrollIntoView({
                    behavior:
                        "smooth",

                    block:
                        "nearest"
                });


            } catch (error) {

                console.error(
                    "Generation error:",
                    error
                );


                message.textContent =
                    "❌ Generation failed:\n\n"
                    + error.message;


            } finally {

                generateButton.disabled =
                    false;


                generateButton.textContent =
                    originalText;
            }
        }
    );


    // ============================================================
    // DISPLAY HELPERS
    // ============================================================

    function getLanguageName(
        value
    ) {

        const values = {

            english:
                "English",

            hindi:
                "Hindi",

            hinglish:
                "Hinglish"
        };


        return (
            values[value]
            || value
        );
    }


    function getToneName(
        value
    ) {

        const values = {

            natural:
                "Natural Human",

            professional:
                "Professional News",

            energetic:
                "Energetic YouTuber",

            friendly:
                "Friendly Explainer",

            breaking:
                "Breaking News",

            calm:
                "Calm & Informative"
        };


        return (
            values[value]
            || value
        );
    }


    function getVoiceName(
        value
    ) {

        const values = {

            // English

            "en-US-AndrewNeural":
                "Andrew — Warm & Confident",

            "en-US-ChristopherNeural":
                "Christopher — Professional",

            "en-US-BrianNeural":
                "Brian — Casual & Approachable",

            "en-US-GuyNeural":
                "Guy — News & Passion",

            "en-US-JennyNeural":
                "Jenny — Friendly",

            "en-US-EmmaNeural":
                "Emma — Cheerful & Clear",


            // Hindi

            "hi-IN-MadhurNeural":
                "Madhur — Hindi Male",

            "hi-IN-SwaraNeural":
                "Swara — Hindi Female",


            // Hinglish / Indian English

            "en-IN-PrabhatNeural":
                "Prabhat — Indian Male",

            "en-IN-NeerjaNeural":
                "Neerja — Indian Female"
        };


        return (
            values[value]
            || value
        );
    }


    function getVisualName(
        value
    ) {

        const values = {

            "modern-news":
                "Modern News",

            "breaking-news":
                "Breaking News",

            "minimal-tech":
                "Minimal Tech",

            "dark-tech":
                "Dark Tech",

            "clean-editorial":
                "Clean Editorial"
        };


        return (
            values[value]
            || value
        );
    }


    function getPrivacyName(
        value
    ) {

        const values = {

            private:
                "Private",

            unlisted:
                "Unlisted",

            public:
                "Public"
        };


        return (
            values[value]
            || value
        );
    }


    // ============================================================
    // INITIAL STATE
    // ============================================================

    updateTopic();

    updatePrivacy();

    updateVoicesForLanguage();

});