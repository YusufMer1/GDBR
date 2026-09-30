document.addEventListener("DOMContentLoaded", function () {

    const favoriteRow =
        document.getElementById("favorite-games-row");

    const favoritePrev =
        document.getElementById("favorite-prev");

    const favoriteNext =
        document.getElementById("favorite-next");


    if (!favoriteRow || !favoritePrev || !favoriteNext) {
        return;
    }


    // SAĞA KAYDIR
    favoriteNext.addEventListener("click", function () {

        favoriteRow.scrollBy({
            left: 580,
            behavior: "smooth"
        });

    });


    // SOLA KAYDIR
    favoritePrev.addEventListener("click", function () {

        favoriteRow.scrollBy({
            left: -580,
            behavior: "smooth"
        });

    });

});