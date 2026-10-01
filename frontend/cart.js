const API_BASE = ["localhost", "127.0.0.1"].includes(location.hostname) ? "http://127.0.0.1:8000" : location.origin;
const API = `${API_BASE}/api/v1`;
const token = localStorage.getItem("olimpiadas_token");
const byId = (id) => document.getElementById(id);
let cart = null;

function imageUrl(path) { return path?.startsWith("http") ? path : `${API_BASE}${path || ""}`; }
function money(amount, currency) { return `${currency === "USD" ? "US$" : "$"}${Number(amount || 0).toLocaleString("es-AR", { maximumFractionDigits: 2 })} ${currency || "ARS"}`; }
async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (!response.ok) { const body = await response.json().catch(() => ({})); const error = new Error(body.detail || `Error ${response.status}`); error.status = response.status; throw error; }
  return response.status === 204 ? null : response.json();
}
function render() {
  const items = cart?.items || [];
  byId("cartEmpty").hidden = items.length > 0;
  byId("cartFooter").hidden = items.length === 0;
  byId("checkoutButton").disabled = items.length === 0;
  byId("clearCartButton").hidden = items.length === 0;
  byId("cartExpiry").textContent = cart?.expires_at ? `Reservamos tu selección hasta el ${new Intl.DateTimeFormat("es-AR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(cart.expires_at))}.` : "";
  const list = byId("cartItems"); list.replaceChildren();
  for (const item of items) list.append(itemRow(item));
  const totals = byId("cartTotals"); totals.replaceChildren();
  for (const total of cart?.totals || []) { const amount = document.createElement("span"); amount.textContent = money(total.amount, total.currency); totals.append(amount); }
}
function itemRow(item) {
  const row = document.createElement("article"); row.className = "cart-item";
  const image = document.createElement("img"); image.className = "cart-item-image"; image.alt = ""; image.src = item.image_url ? imageUrl(item.image_url) : ""; if (!item.image_url) image.hidden = true; image.onerror = () => image.hidden = true;
  const info = document.createElement("div"); info.className = "cart-item-info"; info.innerHTML = `<h3></h3><p></p><p></p>`; info.querySelector("h3").textContent = item.product_name; info.querySelector("p").textContent = item.destination; info.querySelectorAll("p")[1].textContent = `${money(item.unit_price, item.currency)} c/u`;
  const controls = document.createElement("div"); controls.className = "cart-item-controls";
  for (const [label, quantity] of [["−", item.quantity - 1], ["+", item.quantity + 1]]) { const button = document.createElement("button"); button.className = "button button-quiet"; button.type = "button"; button.textContent = label; button.disabled = label === "+" && item.availability_mode === "finite" && quantity > (item.available_units ?? 0); button.addEventListener("click", () => quantity < 1 ? remove(item.id) : update(item.id, quantity)); controls.append(button); if (label === "−") { const count = document.createElement("span"); count.textContent = item.quantity; controls.append(count); } }
  const removeButton = document.createElement("button"); removeButton.className = "text-button"; removeButton.type = "button"; removeButton.textContent = "Quitar"; removeButton.addEventListener("click", () => remove(item.id)); controls.append(removeButton);
  const total = document.createElement("strong"); total.className = "cart-line-total"; total.textContent = money(item.line_total, item.currency); row.append(image, info, controls, total); return row;
}
async function update(id, quantity) { try { cart = await api(`/cart/items/${id}`, { method: "PATCH", body: JSON.stringify({ quantity }) }); render(); } catch (error) { byId("cartMessage").textContent = error.message; } }
async function remove(id) { try { cart = await api(`/cart/items/${id}`, { method: "DELETE" }); render(); } catch (error) { byId("cartMessage").textContent = error.message; } }
byId("clearCartButton").addEventListener("click", async () => { if (!cart?.items?.length || !confirm("¿Querés quitar todos los productos del carrito?")) return; cart = await api("/cart", { method: "DELETE" }); render(); });
byId("checkoutButton").addEventListener("click", async () => {
  if (!cart?.items?.length || !confirm("¿Confirmás la compra simulada? La reserva quedará registrada en tu perfil.")) return;
  const button = byId("checkoutButton"); button.disabled = true; button.textContent = "Confirmando…";
  try {
    const reservation = await api("/cart/checkout", { method: "POST" });
    location.assign(`profile.html?reserva=${encodeURIComponent(reservation.sale_number)}`);
  } catch (error) { byId("cartMessage").textContent = error.message; button.disabled = false; button.textContent = "Confirmar compra"; }
});
(async () => { if (!token) { byId("cartMessage").innerHTML = 'Iniciá sesión desde <a href="index.html">Explorar</a> para ver tu carrito.'; return; } try { cart = await api("/cart"); render(); } catch (error) { byId("cartMessage").textContent = error.status === 401 ? "Tu sesión venció. Volvé a explorar para ingresar nuevamente." : error.message; } })();
