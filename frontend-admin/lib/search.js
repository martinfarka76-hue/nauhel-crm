/**
 * Normalizuje text pro vyhledávání bez ohledu na diakritiku a velikost
 * písmen - "Čanda" i "Canda" po normalizaci dají "canda", takže se
 * najdou navzájem. Použij na OBOU stranách porovnání (hledaný text i
 * prohledávaná pole).
 */
export function normalizeForSearch(value) {
  return (value || "")
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}
