const API_BASE = ["localhost", "127.0.0.1"].includes(location.hostname) ? "http://127.0.0.1:8000" : "https://olimpiadas-v004.onrender.com";
const token = localStorage.getItem("olimpiadas_token");
const byId = (id) => document.getElementById(id);
function money(amount, currency) { return `${currency === "USD" ? "US$" : "$"}${Number(amount || 0).toLocaleString("es-AR", { maximumFractionDigits: 2 })} ${currency || "ARS"}`; }
function emailOrder(item, currency) {
  const unitPrice = Number(item.total || 0) / Math.max(Number(item.quantity || 1), 1);
  return {
    image_url: new URL("img/logo_192x192 .png", location.href).href,
    name: item.product_name,
    units: item.quantity,
    price: money(unitPrice, currency),
    cost: money(item.total, currency),
  };
}
function statusName(status) { return ({ pending_payment: "Pendiente de pago", confirmed: "Confirmada", cancelled: "Cancelada", refund_pending: "Reintegro pendiente", refunded: "Reintegrada" })[status] || status; }
async function loadProfile() {
  if (!token) { location.replace("index.html"); return; }
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw Object.assign(new Error(body.detail || "No pudimos cargar tu perfil"), { status: response.status }); }
    render(await response.json());
  } catch (error) {
    if (error.status === 401) { localStorage.removeItem("olimpiadas_token"); location.replace("index.html"); return; }
    byId("profileMessage").textContent = error.message;
  }
}
function render(profile) {
  byId("profileContent").hidden = false;
  byId("profileName").textContent = profile.full_name;
  byId("profileEmail").textContent = profile.email;
  byId("profilePhone").textContent = profile.phone || "No informado";
  byId("profileInitials").textContent = profile.full_name.split(/\s+/).slice(0, 2).map((name) => name[0]).join("").toUpperCase();
  const reservations = profile.reservations || [];
  byId("reservationCount").textContent = `${reservations.length} ${reservations.length === 1 ? "reserva" : "reservas"}`;
  byId("reservationsEmpty").hidden = reservations.length > 0;
  const container = byId("reservations"); container.replaceChildren();
  for (const reservation of reservations) {
    const card = document.createElement("article"); card.className = "reservation-card";
    const date = new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" }).format(new Date(reservation.purchased_at));
    const items = reservation.items.map((item) => `<li><span>${item.quantity} × ${item.product_name}<small>${item.destination}</small></span><strong>${money(item.total, reservation.currency)}</strong></li>`).join("");
    card.innerHTML = `<div class="reservation-top"><div><span class="reservation-number">${reservation.sale_number}</span><time>${date}</time></div><span class="reservation-status status-${reservation.status}">${statusName(reservation.status)}</span></div><ul>${items}</ul><div class="reservation-total"><span>Total</span><strong>${money(reservation.total, reservation.currency)}</strong></div>`;
    if (reservation.can_cancel) {
      const cancel = document.createElement("button"); cancel.className = "text-button cancel-reservation"; cancel.type = "button"; cancel.textContent = "Cancelar reserva";
      cancel.addEventListener("click", () => cancelReservation(reservation, profile.email, cancel)); card.append(cancel);
    }
    container.append(card);
  }
}
async function cancelReservation(reservation, email, button) {
  if (!confirm(`¿Querés cancelar la reserva ${reservation.sale_number}? Se restaurará la disponibilidad.`)) return;
  button.disabled = true; button.textContent = "Cancelando…";
  try {
    const response = await fetch(`${API_BASE}/api/v1/cart/reservations/${encodeURIComponent(reservation.sale_number)}/cancel`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || "No se pudo cancelar la reserva"); }
    await sendTransactionEmail({
      email,
      orderId: reservation.sale_number,
      orders: reservation.items.map((item) => emailOrder(item, reservation.currency)),
      cost: money(reservation.total, reservation.currency),
      status: "cancelled",
    });
    await loadProfile();
  } catch (error) { button.disabled = false; button.textContent = "Cancelar reserva"; alert(error.message); }
}
byId("logoutButton").addEventListener("click", () => { localStorage.removeItem("olimpiadas_token"); location.assign("index.html"); });
loadProfile();
