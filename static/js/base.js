document.addEventListener(
    "DOMContentLoaded",
    function () {

        const input =
            document.getElementById(
                "navbar-search-input"
            );

        const typeSelect =
            document.getElementById(
                "navbar-search-type"
            );

        const suggestions =
            document.getElementById(
                "search-suggestions"
            );


        if (
            !input ||
            !typeSelect ||
            !suggestions
        ) {
            return;
        }


        let searchTimeout = null;

        let currentController = null;

        let lastRequestId = 0;


        // Aynı sorguyu tekrar API'ye göndermemek için.
        const searchCache = new Map();



        /* =====================================================
           CLOSE
        ====================================================== */

        function closeSuggestions() {

            suggestions.classList.remove(
                "open"
            );

        }



        /* =====================================================
           ICON
        ====================================================== */

        function getIcon(type) {

            if (type === "library") {
                return "📚";
            }

            if (type === "user") {
                return "👤";
            }

            return "🎮";

        }



        /* =====================================================
           RESULT URL
        ====================================================== */

        function buildUrl(item) {

            if (item.type === "game") {

                return (
                    "/game/igdb/" +
                    item.id +
                    "/"
                );

            }


            if (item.type === "library") {

                return (
                    "/libraries/" +
                    item.id +
                    "/"
                );

            }


            /*
             * Public user profile henüz yok.
             * Şimdilik user search sayfasına götürüyoruz.
             */

            return (
                "/search/?q=" +
                encodeURIComponent(
                    item.title
                ) +
                "&type=users"
            );

        }



        /* =====================================================
           RENDER
        ====================================================== */

        function renderResults(results) {

            suggestions.innerHTML = "";


            if (
                !results ||
                results.length === 0
            ) {

                suggestions.innerHTML =
                    `
                    <div class="search-suggestions-empty">
                        No results found
                    </div>
                    `;

                suggestions.classList.add(
                    "open"
                );

                return;
            }


            results.forEach(
                function (item) {

                    const link =
                        document.createElement(
                            "a"
                        );


                    link.className =
                        "search-suggestion-item";


                    link.href =
                        buildUrl(item);



                    /* ICON */

                    const icon =
                        document.createElement(
                            "span"
                        );


                    icon.className =
                        "search-suggestion-icon";


                    icon.textContent =
                        getIcon(
                            item.type
                        );



                    /* INFO */

                    const info =
                        document.createElement(
                            "span"
                        );


                    info.className =
                        "search-suggestion-info";



                    /* TITLE */

                    const title =
                        document.createElement(
                            "strong"
                        );


                    title.textContent =
                        item.title;



                    /* SUBTITLE */

                    const subtitle =
                        document.createElement(
                            "small"
                        );


                    subtitle.textContent =
                        item.subtitle || "";



                    info.appendChild(
                        title
                    );


                    info.appendChild(
                        subtitle
                    );


                    link.appendChild(
                        icon
                    );


                    link.appendChild(
                        info
                    );


                    suggestions.appendChild(
                        link
                    );

                }
            );


            suggestions.classList.add(
                "open"
            );

        }



        /* =====================================================
           SEARCH
        ====================================================== */

        async function loadSuggestions() {

            const query =
                input.value.trim();


            const searchType =
                typeSelect.value;



            /*
             * Games IGDB kullandığı için minimum 3 karakter.
             * Users/Libraries DB'de olduğu için 2 karakter.
             */

            const minimumLength =
                searchType === "games"
                    ? 3
                    : 2;


            if (
                query.length < minimumLength
            ) {

                suggestions.innerHTML = "";

                closeSuggestions();

                return;

            }



            const cacheKey =
                searchType +
                ":" +
                query.toLowerCase();



            /* =================================================
               CACHE
            ================================================== */

            if (
                searchCache.has(
                    cacheKey
                )
            ) {

                renderResults(
                    searchCache.get(
                        cacheKey
                    )
                );

                return;

            }



            /* =================================================
               CANCEL PREVIOUS REQUEST
            ================================================== */

            if (currentController) {

                currentController.abort();

            }


            currentController =
                new AbortController();


            const requestId =
                ++lastRequestId;



            try {

                const params =
                    new URLSearchParams({
                        q: query,
                        type: searchType
                    });


                const response =
                    await fetch(
                        "/search/suggestions/?" +
                        params.toString(),
                        {
                            signal:
                                currentController.signal,

                            headers: {
                                "X-Requested-With":
                                    "XMLHttpRequest"
                            }
                        }
                    );


                if (!response.ok) {
                    return;
                }


                const data =
                    await response.json();



                /*
                 * Eğer kullanıcı bu sırada yeni bir
                 * arama yaptıysa eski sonucu göstermiyoruz.
                 */

                if (
                    requestId !==
                    lastRequestId
                ) {

                    return;

                }



                const results =
                    data.results || [];


                searchCache.set(
                    cacheKey,
                    results
                );


                renderResults(
                    results
                );


            } catch (error) {

                if (
                    error.name !==
                    "AbortError"
                ) {

                    console.error(
                        "Autocomplete error:",
                        error
                    );

                }

            }

        }



        /* =====================================================
           INPUT
        ====================================================== */

        input.addEventListener(
            "input",
            function () {

                clearTimeout(
                    searchTimeout
                );


                const searchType =
                    typeSelect.value;



                /*
                 * Local DB aramaları daha hızlı.
                 * IGDB'ye biraz daha fazla debounce.
                 */

                const delay =
                    searchType === "games"
                        ? 220
                        : 120;


                searchTimeout =
                    setTimeout(
                        loadSuggestions,
                        delay
                    );

            }
        );



        /* =====================================================
           SEARCH TYPE CHANGED
        ====================================================== */

        typeSelect.addEventListener(
            "change",
            function () {

                clearTimeout(
                    searchTimeout
                );


                suggestions.innerHTML = "";


                loadSuggestions();

            }
        );



        /* =====================================================
           INPUT FOCUS
        ====================================================== */

        input.addEventListener(
            "focus",
            function () {

                const query =
                    input.value.trim();


                const searchType =
                    typeSelect.value;


                const minimumLength =
                    searchType === "games"
                        ? 3
                        : 2;


                if (
                    query.length >=
                    minimumLength
                ) {

                    loadSuggestions();

                }

            }
        );



        /* =====================================================
           CLICK OUTSIDE
        ====================================================== */

        document.addEventListener(
            "click",
            function (event) {

                if (
                    !event.target.closest(
                        ".navbar-search-wrapper"
                    )
                ) {

                    closeSuggestions();

                }

            }
        );



        /* =====================================================
           ESCAPE
        ====================================================== */

        input.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Escape"
                ) {

                    closeSuggestions();

                }

            }
        );

    }


    
);

/* =========================================================
   GDBR AI
========================================================= */

const gdbrAiRoot =
    document.querySelector(
        ".gdbr-ai"
    );

const gdbrAiToggle =
    document.getElementById(
        "gdbr-ai-toggle"
    );

const gdbrAiPanel =
    document.getElementById(
        "gdbr-ai-panel"
    );

const gdbrAiClose =
    document.getElementById(
        "gdbr-ai-close"
    );

const gdbrAiForm =
    document.getElementById(
        "gdbr-ai-form"
    );

const gdbrAiInput =
    document.getElementById(
        "gdbr-ai-input"
    );

const gdbrAiMessages =
    document.getElementById(
        "gdbr-ai-messages"
    );

const gdbrAiSend =
    document.getElementById(
        "gdbr-ai-send"
    );


/* =========================================================
   OPEN CHAT
========================================================= */

function openGdbrAi() {

    if (
        !gdbrAiRoot ||
        !gdbrAiPanel ||
        !gdbrAiToggle
    ) {
        return;
    }

    gdbrAiRoot.classList.add(
        "is-open"
    );

    gdbrAiPanel.classList.add(
        "open"
    );

    gdbrAiToggle.classList.add(
        "chat-open"
    );

    gdbrAiToggle.setAttribute(
        "aria-expanded",
        "true"
    );

    gdbrAiToggle.setAttribute(
        "aria-label",
        "Close GDBR Assistant"
    );

    setTimeout(
        function () {

            if (gdbrAiInput) {
                gdbrAiInput.focus();
            }

        },
        320
    );
}


/* =========================================================
   CLOSE CHAT
========================================================= */

function closeGdbrAi() {

    if (
        !gdbrAiRoot ||
        !gdbrAiPanel ||
        !gdbrAiToggle
    ) {
        return;
    }

    gdbrAiRoot.classList.remove(
        "is-open"
    );

    gdbrAiPanel.classList.remove(
        "open"
    );

    gdbrAiToggle.classList.remove(
        "chat-open"
    );

    gdbrAiToggle.setAttribute(
        "aria-expanded",
        "false"
    );

    gdbrAiToggle.setAttribute(
        "aria-label",
        "Open GDBR Assistant"
    );
}


/* =========================================================
   ROBOT BUTTON
========================================================= */

if (
    gdbrAiToggle &&
    gdbrAiPanel
) {

    gdbrAiToggle.setAttribute(
        "aria-expanded",
        "false"
    );

    gdbrAiToggle.addEventListener(
        "click",
        function () {

            const isOpen =
                gdbrAiPanel.classList.contains(
                    "open"
                );

            if (isOpen) {
                closeGdbrAi();
            } else {
                openGdbrAi();
            }

        }
    );
}


/* =========================================================
   CLOSE BUTTON
========================================================= */

if (gdbrAiClose) {

    gdbrAiClose.addEventListener(
        "click",
        closeGdbrAi
    );
}


/* =========================================================
   ESCAPE TO CLOSE
========================================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Escape" &&
            gdbrAiPanel &&
            gdbrAiPanel.classList.contains(
                "open"
            )
        ) {
            closeGdbrAi();
        }

    }
);


/* =========================================================
   ADD MESSAGE
========================================================= */

function addAiMessage(
    text,
    type
) {

    if (!gdbrAiMessages) {
        return;
    }

    const message =
        document.createElement(
            "div"
        );

    message.className =
        `gdbr-ai-message ${type}`;

    message.textContent =
        text;

    gdbrAiMessages.appendChild(
        message
    );

    gdbrAiMessages.scrollTop =
        gdbrAiMessages.scrollHeight;
}


/* =========================================================
   TYPING MESSAGE
========================================================= */

function removeTypingMessage() {

    if (!gdbrAiMessages) {
        return;
    }

    const typingMessage =
        gdbrAiMessages.querySelector(
            ".gdbr-ai-typing"
        );

    if (typingMessage) {
        typingMessage.remove();
    }
}


function addTypingMessage() {

    if (!gdbrAiMessages) {
        return;
    }

    removeTypingMessage();

    const message =
        document.createElement(
            "div"
        );

    message.className =
        "gdbr-ai-message assistant gdbr-ai-typing";

    message.textContent =
        "Thinking...";

    gdbrAiMessages.appendChild(
        message
    );

    gdbrAiMessages.scrollTop =
        gdbrAiMessages.scrollHeight;
}


/* =========================================================
   CSRF TOKEN
========================================================= */

function getCsrfToken() {

    const csrfInput =
        document.querySelector(
            "#gdbr-ai-form input[name='csrfmiddlewaretoken']"
        );

    return csrfInput
        ? csrfInput.value
        : "";
}


/* =========================================================
   SUBMIT MESSAGE
========================================================= */

if (
    gdbrAiForm &&
    gdbrAiInput &&
    gdbrAiSend
) {

    gdbrAiForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();

            const question =
                gdbrAiInput.value.trim();

            if (!question) {
                return;
            }

            addAiMessage(
                question,
                "user"
            );

            gdbrAiInput.value =
                "";

            gdbrAiSend.disabled =
                true;

            gdbrAiSend.textContent =
                "...";

            addTypingMessage();

            try {

                const response =
                    await fetch(
                        gdbrAiForm.action,
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                "X-CSRFToken":
                                    getCsrfToken(),

                                "X-Requested-With":
                                    "XMLHttpRequest",
                            },

                            body:
                                JSON.stringify(
                                    {
                                        question:
                                            question
                                    }
                                ),
                        }
                    );

                const contentType =
                    response.headers.get(
                        "content-type"
                    ) || "";

                if (
                    !contentType.includes(
                        "application/json"
                    )
                ) {

                    const rawText =
                        await response.text();

                    console.error(
                        "GDBR AI returned non-JSON response:",
                        response.status,
                        rawText
                    );

                    removeTypingMessage();

                    addAiMessage(
                        "The AI assistant could not connect to the server.",
                        "assistant"
                    );

                    return;
                }

                const data =
                    await response.json();

                if (!response.ok) {

                    console.error(
                        "GDBR AI SERVER ERROR:",
                        response.status,
                        data
                    );

                    removeTypingMessage();

                    addAiMessage(
                        data.error ||
                        "Something went wrong.",
                        "assistant"
                    );

                    return;
                }

                removeTypingMessage();

                addAiMessage(
                    data.answer ||
                    "The AI assistant returned an empty response.",
                    "assistant"
                );

            } catch (error) {

                console.error(
                    "GDBR AI FETCH ERROR:",
                    error
                );

                removeTypingMessage();

                addAiMessage(
                    "The AI assistant is temporarily unavailable.",
                    "assistant"
                );

            } finally {

                gdbrAiSend.disabled =
                    false;

                gdbrAiSend.textContent =
                    "Send";

                gdbrAiInput.focus();
            }

        }
    );
}


/* =========================================================
   ENTER TO SEND
   SHIFT + ENTER = NEW LINE
========================================================= */

if (gdbrAiInput) {

    gdbrAiInput.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                if (
                    gdbrAiForm &&
                    gdbrAiSend &&
                    !gdbrAiSend.disabled
                ) {
                    gdbrAiForm.requestSubmit();
                }
            }

        }
    );
}