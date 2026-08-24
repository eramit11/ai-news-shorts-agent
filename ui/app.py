from flask import (
    Flask,
    jsonify,
    render_template,
    request,
)

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
)


# ============================================================
# CACHE CONTROL
# ============================================================

@app.after_request
def add_no_cache_headers(response):
    response.headers[
        "Cache-Control"
    ] = "no-store, no-cache, must-revalidate"

    response.headers[
        "Pragma"
    ] = "no-cache"

    response.headers[
        "Expires"
    ] = "0"

    return response


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return render_template(
        "index.html"
    )


# ============================================================
# GENERATE SHORT
# ============================================================

@app.post("/api/generate")
def generate():

    try:

        from app.pipeline import (
            run_pipeline
        )

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        # ----------------------------------------------------
        # READ UI VALUES
        # ----------------------------------------------------

        topic = data.get(
            "topic",
            "top-ai-news",
        )

        language = data.get(
            "language",
            "english",
        )

        tone = data.get(
            "tone",
            "natural",
        )

        voice = data.get(
            "voice",
            "en-US-ChristopherNeural",
        )

        visual = data.get(
            "visual",
            "modern-news",
        )

        privacy = data.get(
            "privacy",
            "private",
        )

        # ----------------------------------------------------
        # NUMERIC VALUES
        # ----------------------------------------------------

        try:
            stories = int(
                data.get(
                    "stories",
                    3,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            stories = 3

        try:
            duration = int(
                data.get(
                    "duration",
                    24,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            duration = 24

        # ----------------------------------------------------
        # UPLOAD VALUE
        #
        # IMPORTANT:
        # bool("false") == True in Python.
        #
        # Therefore parse explicitly.
        # ----------------------------------------------------

        upload_value = data.get(
            "upload",
            False,
        )

        if isinstance(
            upload_value,
            bool,
        ):

            upload = upload_value

        elif isinstance(
            upload_value,
            str,
        ):

            upload = (
                upload_value
                .strip()
                .lower()
                in {
                    "true",
                    "1",
                    "yes",
                    "on",
                }
            )

        else:

            upload = bool(
                upload_value
            )

        # ----------------------------------------------------
        # LOG REQUEST
        # ----------------------------------------------------

        print(
            "",
            flush=True,
        )

        print(
            "======================================",
            flush=True,
        )

        print(
            "UI GENERATE REQUEST",
            flush=True,
        )

        print(
            "======================================",
            flush=True,
        )

        print(
            f"Topic: {topic}",
            flush=True,
        )

        print(
            f"Language: {language}",
            flush=True,
        )

        print(
            f"Tone: {tone}",
            flush=True,
        )

        print(
            f"Voice: {voice}",
            flush=True,
        )

        print(
            f"Stories: {stories}",
            flush=True,
        )

        print(
            f"Duration: {duration}",
            flush=True,
        )

        print(
            f"Visual: {visual}",
            flush=True,
        )

        print(
            f"YouTube upload: {upload}",
            flush=True,
        )

        print(
            f"YouTube privacy: {privacy}",
            flush=True,
        )

        # ----------------------------------------------------
        # RUN PIPELINE
        # ----------------------------------------------------

        result = run_pipeline(
            topic=topic,
            language=language,
            tone=tone,
            voice=voice,
            stories=stories,
            duration=duration,
            visual_style=visual,
            upload=upload,
            privacy=privacy,
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return jsonify(
            {
                "success": True,
                "result": result,
            }
        )

    except Exception as exc:

        import traceback

        print(
            "",
            flush=True,
        )

        print(
            "UI PIPELINE ERROR",
            flush=True,
        )

        print(
            str(exc),
            flush=True,
        )

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )