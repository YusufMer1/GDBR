document.addEventListener("DOMContentLoaded", function () {

    const loader = document.getElementById("game-media-loader");
    const videosContainer = document.getElementById("game-videos");
    const mainScreenshotContainer = document.getElementById(
        "screenshot-main-container"
    );
    const thumbnailsContainer = document.getElementById(
        "screenshot-thumbnails"
    );

    if (!loader) {
        return;
    }

    const mediaUrl = loader.dataset.mediaUrl;

    if (!mediaUrl) {
        return;
    }

    fetch(mediaUrl)
        .then(function (response) {

            if (!response.ok) {
                throw new Error(
                    "Media request failed: " + response.status
                );
            }

            return response.json();

        })
        .then(function (data) {

            renderVideos(
                data.videos || [],
                videosContainer
            );

            renderScreenshots(
                data.screenshots || [],
                mainScreenshotContainer,
                thumbnailsContainer
            );

        })
        .catch(function (error) {

            console.error(
                "GAME MEDIA ERROR:",
                error
            );

            if (videosContainer) {
                videosContainer.innerHTML = `
                    <div class="game-media-empty">
                        Video could not be loaded.
                    </div>
                `;
            }

            if (mainScreenshotContainer) {
                mainScreenshotContainer.innerHTML = `
                    <div class="game-media-empty">
                        Screenshots could not be loaded.
                    </div>
                `;
            }

            if (thumbnailsContainer) {
                thumbnailsContainer.innerHTML = "";
            }

        });


    function renderVideos(videos, container) {

        if (!container) {
            return;
        }

        if (!videos.length) {

            container.innerHTML = `
                <div class="game-media-empty">
                    No video available.
                </div>
            `;

            return;
        }

        const video = videos[0];

        const videoId =
            video.video_id ||
            video.videoId ||
            video.id;

        if (!videoId) {

            container.innerHTML = `
                <div class="game-media-empty">
                    No video available.
                </div>
            `;

            return;
        }

        container.innerHTML = `
            <iframe
                src="https://www.youtube.com/embed/${videoId}?origin=${encodeURIComponent(window.location.origin)}"
                title="Game video"
                loading="lazy"
                referrerpolicy="strict-origin-when-cross-origin"
                allow="
                    accelerometer;
                    autoplay;
                    clipboard-write;
                    encrypted-media;
                    gyroscope;
                    picture-in-picture;
                    web-share
                "
                allowfullscreen
            ></iframe>
        `;

    }


    function renderScreenshots(
        screenshots,
        mainContainer,
        thumbnailsContainer
    ) {

        if (!mainContainer) {
            return;
        }

        if (!screenshots.length) {

            mainContainer.innerHTML = `
                <div class="game-media-empty">
                    No screenshots available.
                </div>
            `;

            if (thumbnailsContainer) {
                thumbnailsContainer.innerHTML = "";
            }

            return;
        }

        const normalizedScreenshots =
            screenshots
                .map(function (screenshot) {

                    if (typeof screenshot === "string") {
                        return screenshot;
                    }

                    if (screenshot.url) {
                        return normalizeImageUrl(
                            screenshot.url
                        );
                    }

                    if (screenshot.image_id) {
                        return (
                            "https://images.igdb.com/" +
                            "igdb/image/upload/" +
                            "t_1080p/" +
                            screenshot.image_id +
                            ".jpg"
                        );
                    }

                    return null;

                })
                .filter(Boolean);


        if (!normalizedScreenshots.length) {

            mainContainer.innerHTML = `
                <div class="game-media-empty">
                    No screenshots available.
                </div>
            `;

            return;
        }


        mainContainer.innerHTML = `
            <img
                id="main-screenshot"
                src="${normalizedScreenshots[0]}"
                alt="Game screenshot"
            >
        `;


        if (!thumbnailsContainer) {
            return;
        }


        thumbnailsContainer.innerHTML =
            normalizedScreenshots
                .map(function (url, index) {

                    return `
                        <button
                            type="button"
                            class="screenshot-thumb ${
                                index === 0
                                    ? "active"
                                    : ""
                            }"
                            data-image="${url}"
                        >
                            <img
                                src="${url}"
                                alt="Screenshot ${index + 1}"
                                loading="lazy"
                            >
                        </button>
                    `;

                })
                .join("");


        attachScreenshotEvents();

    }


    function attachScreenshotEvents() {

        const mainImage =
            document.getElementById(
                "main-screenshot"
            );

        const thumbnails =
            document.querySelectorAll(
                ".screenshot-thumb"
            );

        if (
            !mainImage ||
            thumbnails.length === 0
        ) {
            return;
        }


        thumbnails.forEach(function (thumbnail) {

            thumbnail.addEventListener(
                "click",
                function () {

                    const newImage =
                        this.getAttribute(
                            "data-image"
                        );

                    if (!newImage) {
                        return;
                    }


                    thumbnails.forEach(
                        function (item) {

                            item.classList.remove(
                                "active"
                            );

                        }
                    );


                    this.classList.add(
                        "active"
                    );


                    mainImage.style.opacity =
                        "0";


                    setTimeout(
                        function () {

                            mainImage.src =
                                newImage;

                            mainImage.style.opacity =
                                "1";

                        },
                        150
                    );

                }
            );

        });

    }


    function normalizeImageUrl(url) {

        if (!url) {
            return "";
        }

        if (url.startsWith("//")) {
            return "https:" + url;
        }

        return url;

    }

});