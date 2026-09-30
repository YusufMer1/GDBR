document.addEventListener("DOMContentLoaded", function () {

    const row = document.getElementById("series-row");
    const prev = document.getElementById("series-prev");
    const next = document.getElementById("series-next");

    if (!row || !prev || !next) {
        console.log("Series slider bulunamadı.");
        return;
    }

    console.log("Series slider hazır.");

    function getScrollAmount() {

        const card = row.querySelector(".series-card");

        if (!card) {
            return 0;
        }

        const styles = window.getComputedStyle(row);
        const gap = parseFloat(styles.gap) || 22;

        return (card.offsetWidth + gap) * 3;
    }

    next.addEventListener("click", function (e) {

        e.preventDefault();

        row.scrollBy({
            left: getScrollAmount(),
            behavior: "smooth"
        });

    });

    prev.addEventListener("click", function (e) {

        e.preventDefault();

        row.scrollBy({
            left: -getScrollAmount(),
            behavior: "smooth"
        });

    });

});