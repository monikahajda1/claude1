// Rejestracja PWA (działa tylko przez HTTPS albo na localhost).
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  });
}

// Podpowiedź daty ważności: po wybraniu rodzaju dokumentu i daty wydania
// wylicza „ważny do” na podstawie typowego okresu (tylko gdy pole jest puste).
document.addEventListener("DOMContentLoaded", function () {
  var dane = document.getElementById("okresy-dokumentow");
  if (!dane) return;
  var okresy = JSON.parse(dane.textContent);
  var typ = document.getElementById("id_typ");
  var wydanie = document.getElementById("id_data_wydania");
  var waznosc = document.getElementById("id_data_waznosci");
  function podpowiedz() {
    var mies = okresy[typ.value];
    if (!mies || !wydanie.value || waznosc.value) return;
    var d = new Date(wydanie.value + "T12:00:00");
    d.setMonth(d.getMonth() + mies);
    d.setDate(d.getDate() - 1);
    waznosc.value = d.toISOString().slice(0, 10);
    waznosc.classList.add("is-valid");
  }
  typ.addEventListener("change", podpowiedz);
  wydanie.addEventListener("change", podpowiedz);
});
