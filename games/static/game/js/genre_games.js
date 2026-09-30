document.addEventListener("DOMContentLoaded", function () {

    const genreButtons =
        document.querySelectorAll(".genre-button");

    const gameRow =
        document.getElementById("genre-games-row");

    const prevButton =
        document.getElementById("genre-prev");

    const nextButton =
        document.getElementById("genre-next");


    if (!gameRow || genreButtons.length === 0) {
        return;
    }


    // ===============================
    // GENRE YÜKLE
    // ===============================

    function loadGenre(genreId) {

        gameRow.innerHTML =
            '<div class="genre-loading">Loading games...</div>';


        const section = document.querySelector(".genre-discover-section");

        const url = section.dataset.genreUrl.replace(
            "999999",
            genreId
        );

        fetch(url)
            .then(function(response) {

                if (!response.ok) {
                    throw new Error(
                        `HTTP error: ${response.status}`
                    );
                }

                return response.text();
            })
            .then(function(html) {

                gameRow.innerHTML = html;
                gameRow.scrollLeft = 0;

            })
            .catch(function(error) {

                console.error("Genre games error:", error);

                gameRow.innerHTML =
                    '<div class="genre-loading">Games could not be loaded.</div>';
            });

    }


    // ===============================
    // GENRE BUTTON
    // ===============================

    genreButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            genreButtons.forEach(function (item) {
                item.classList.remove("active");
            });

            button.classList.add("active");


            const genreId =
                button.dataset.genreId;

            loadGenre(genreId);

        });

    });


    // ===============================
    // SAĞ OK
    // ===============================

    if (nextButton) {

        nextButton.addEventListener("click", function () {

            gameRow.scrollBy({
                left: 750,
                behavior: "smooth"
            });

        });

    }


    // ===============================
    // SOL OK
    // ===============================

    if (prevButton) {

        prevButton.addEventListener("click", function () {

            gameRow.scrollBy({
                left: -750,
                behavior: "smooth"
            });

        });

    }


    // ===============================
    // BAŞLANGIÇTA ACTION YÜKLE
    // ===============================

    const firstGenre =
        document.querySelector(".genre-button.active");

    if (firstGenre) {
        loadGenre(firstGenre.dataset.genreId);
    }

});