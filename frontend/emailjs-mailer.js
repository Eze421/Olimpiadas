function emailJsIsConfigured() {
  const config = window.EMAILJS_CONFIG || {};
  return Boolean(window.emailjs && config.publicKey && config.serviceId && config.templateId);
}

async function sendTransactionEmail({ email, orderId, orders, cost, status }) {
  if (!emailJsIsConfigured()) return false;
  const config = window.EMAILJS_CONFIG;
  const firstOrder = orders[0] || {};
  const subject = status === "cancelled" ? `Reserva cancelada · ${orderId}` : `Reserva confirmada · ${orderId}`;
  const message = status === "cancelled"
    ? `Confirmamos la cancelación de tu reserva ${orderId}. La disponibilidad fue restaurada.`
    : `Tu reserva ${orderId} fue confirmada. Podés verla desde tu perfil.`;
  try {
    await window.emailjs.send(config.serviceId, config.templateId, {
      // Campos para la plantilla de EmailJS configurada en el panel.
      email,
      to_email: email,
      order_id: orderId,
      orders,
      image_url: firstOrder.image_url || "",
      name: firstOrder.name || "",
      units: firstOrder.units || 0,
      price: firstOrder.price || "",
      cost,
      subject,
      message,
      status,
    }, { publicKey: config.publicKey });
    return true;
  } catch (error) {
    console.warn("No se pudo enviar el correo por EmailJS", error);
    return false;
  }
}
