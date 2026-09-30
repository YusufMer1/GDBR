document.addEventListener("DOMContentLoaded", function () {

    const mainImage = document.getElementById("main-screenshot");

    const thumbnails = document.querySelectorAll(".screenshot-thumb");

    if (!mainImage || thumbnails.length === 0) {
        return;
    }

    thumbnails.forEach(function (thumbnail) {

        thumbnail.addEventListener("click", function () {

            const newImage = this.getAttribute("data-image");

            if (!newImage) {
                return;
            }

            // bütün küçük resimlerden active'i kaldır
            thumbnails.forEach(function (item) {
                item.classList.remove("active");
            });

            // tıklanana active ekle
            this.classList.add("active");

            // geçiş efekti
            mainImage.style.opacity = "0";

            setTimeout(function () {

                mainImage.src = newImage;

                mainImage.style.opacity = "1";

            }, 150);

        });

    });

});