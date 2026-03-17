/* RareBus UI helpers */

document.addEventListener("DOMContentLoaded", () => {

  /* Auto dismiss notices */

  document.querySelectorAll(".notice").forEach(el => {

    setTimeout(() => {
      el.style.opacity = "0";
      setTimeout(()=>el.remove(),400);
    }, 4000);

  });

  /* Table search (fleet pages) */

  const search = document.querySelector("#fleetSearch");

  if(search){

    search.addEventListener("input", function(){

      const value = this.value.toLowerCase();

      document.querySelectorAll(".fleet-table tbody tr").forEach(row => {

        const text = row.innerText.toLowerCase();

        row.style.display = text.includes(value) ? "" : "none";

      });

    });

  }

});