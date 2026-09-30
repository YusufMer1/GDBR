document.addEventListener("DOMContentLoaded", function () {

    const slides = document.querySelectorAll(".trending-slide");
    const dots = document.querySelectorAll(".trending-dot");

    const prevButton = document.getElementById("trending-prev");
    const nextButton = document.getElementById("trending-next");

    const counter = document.getElementById("trending-current");

    // Slider yoksa kodu durdur
    if (slides.length === 0) {
        return;
    }

    let currentIndex = 0;
    let autoSlide = null;


    // =====================================
    // SLIDE GÖSTER
    // =====================================

    function showSlide(index) {

        // Son oyundan sonra ilk oyuna dön
        if (index >= slides.length) {
            index = 0;
        }

        // İlk oyundan geriye gidersek son oyuna dön
        if (index < 0) {
            index = slides.length - 1;
        }


        // Tüm slide'ların active classını kaldır
        slides.forEach(function (slide) {
            slide.classList.remove("active");
        });


        // Tüm dotların active classını kaldır
        dots.forEach(function (dot) {
            dot.classList.remove("active");
        });


        // Seçilen slide aktif
        slides[index].classList.add("active");


        // Seçilen slide'ın dot'u aktif
        if (dots[index]) {
            dots[index].classList.add("active");
        }


        // Sayacı güncelle
        if (counter) {
            counter.textContent = index + 1;
        }


        // Güncel index
        currentIndex = index;
    }


    // =====================================
    // SONRAKİ
    // =====================================

    function nextSlide() {
        showSlide(currentIndex + 1);
    }


    // =====================================
    // ÖNCEKİ
    // =====================================

    function previousSlide() {
        showSlide(currentIndex - 1);
    }


    // =====================================
    // OTOMATİK GEÇİŞ
    // =====================================

    function startAutoSlide() {

        // Önce eski intervali temizle
        if (autoSlide) {
            clearInterval(autoSlide);
        }

        autoSlide = setInterval(function () {
            nextSlide();
        }, 4000);
    }


    // =====================================
    // SAĞ OK
    // =====================================

    if (nextButton) {

        nextButton.addEventListener("click", function () {

            nextSlide();

            // Kullanıcı tıklayınca 4 saniyeyi yeniden başlat
            startAutoSlide();
        });
    }


    // =====================================
    // SOL OK
    // =====================================

    if (prevButton) {

        prevButton.addEventListener("click", function () {

            previousSlide();

            startAutoSlide();
        });
    }


    // =====================================
    // DOTLARA TIKLAMA
    // =====================================

    dots.forEach(function (dot) {

        dot.addEventListener("click", function () {

            const index = Number(
                dot.dataset.index
            );

            showSlide(index);

            startAutoSlide();
        });
    });


    // =====================================
    // BAŞLANGIÇ
    // =====================================

    showSlide(0);

    startAutoSlide();

});