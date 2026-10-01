const DEFAULT_API_BASE = ["localhost", "127.0.0.1"].includes(location.hostname) ? "http://127.0.0.1:8000" : location.origin;
const requestedApi = new URLSearchParams(location.search).get("api");
let API_BASE = DEFAULT_API_BASE;
if (requestedApi) {
  try {
    const requestedOrigin = new URL(requestedApi).origin;
    const localFrontend = ["localhost", "127.0.0.1"].includes(location.hostname);
    const localBackend = ["localhost", "127.0.0.1"].includes(new URL(requestedOrigin).hostname);
    if (requestedOrigin === location.origin || (localFrontend && localBackend)) API_BASE = requestedOrigin;
  } catch { /* Se ignora una URL de API inválida. */ }
}
const API = `${API_BASE}/api/v1`;
const TYPE_NAMES = {
  accommodation: "Alojamiento",
  flight: "Vuelo",
  car_rental: "Alquiler de auto",
  package: "Paquete",
};

function roleFromToken(token) {
  if (!token) return null;
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload)).role || null;
  } catch { return null; }
}

const state = {
  products: [], filter: "all", query: "", token: localStorage.getItem("olimpiadas_token"),
  role: roleFromToken(localStorage.getItem("olimpiadas_token")),
  cart: null, pendingCartItem: null, currentProduct: null, detailProduct: null, detailImageIndex: 0,
};
const byId = (id) => document.getElementById(id);
const storeView = byId("storeView");
const adminView = byId("adminView");
const productGrid = byId("productGrid");
const productDialog = byId("productDialog");

function imageUrl(path) {
  return path?.startsWith("http") ? path : `${API_BASE}${path || ""}`;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) {
        message = body.detail.map((issue) => {
          const field = Array.isArray(issue.loc) ? issue.loc.slice(1).join(".") : "";
          return `${field ? `${field}: ` : ""}${issue.msg || "Dato inválido"}`;
        }).join("; ");
      }
    } catch { /* Respuesta sin JSON. */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function showToast(message) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.remove("is-visible"), 2800);
}

function setSession(token) {
  state.token = token;
  state.role = roleFromToken(token);
  localStorage.setItem("olimpiadas_token", token);
  byId("accountButton").textContent = state.role === "customer" ? "Mi perfil" : "Salir";
  byId("manageNav").hidden = state.role !== "sales_manager";
  byId("adminTopButton").hidden = state.role !== "sales_manager";
}

function clearSession() {
  state.token = null;
  state.role = null;
  state.cart = null;
  localStorage.removeItem("olimpiadas_token");
  byId("accountButton").textContent = "Ingresar";
  byId("manageNav").hidden = false;
  byId("adminTopButton").hidden = true;
  updateCartCount();
}

function updateCartCount() {
  const count = state.cart?.items?.reduce((sum, item) => sum + item.quantity, 0) || 0;
  byId("cartCount").textContent = String(count);
}

function money(amount, currency) {
  const value = Number(amount || 0).toLocaleString("es-AR", { maximumFractionDigits: 2 });
  return `${currency === "USD" ? "US$" : "$"}${value} ${currency || "ARS"}`;
}

function stockText(product) {
  if (product.availability_mode === "unlimited") return "Disponibilidad ilimitada";
  return `${product.available_units ?? 0} disponibles`;
}

function makePlaceholder() {
  const placeholder = document.createElement("div");
  placeholder.className = "image-placeholder";
  placeholder.setAttribute("aria-hidden", "true");
  placeholder.textContent = "✳";
  return placeholder;
}

function renderProducts() {
  productGrid.replaceChildren();
  const normalizedQuery = state.query.trim().toLocaleLowerCase("es");
  const visible = state.products.filter((product) => {
    const typeMatches = state.filter === "all" || product.product_type === state.filter;
    const text = `${product.name} ${product.destination} ${product.description || ""}`.toLocaleLowerCase("es");
    return typeMatches && text.includes(normalizedQuery);
  });
  byId("emptyState").hidden = visible.length > 0;
  for (const product of visible) productGrid.append(makeProductCard(product));
}

function makeProductCard(product) {
  const card = document.createElement("article");
  card.className = "product-card";
  const imageWrap = document.createElement("div");
  imageWrap.className = "product-image-wrap";
  const image = product.images?.[0];
  if (image) {
    const img = document.createElement("img");
    img.className = "product-image";
    img.src = imageUrl(image.url);
    img.alt = image.alt_text || product.name;
    img.loading = "lazy";
    img.onerror = () => img.replaceWith(makePlaceholder());
    imageWrap.append(img);
  } else imageWrap.append(makePlaceholder());
  const badge = document.createElement("span");
  badge.className = "image-badge";
  badge.textContent = TYPE_NAMES[product.product_type] || "Experiencia";
  imageWrap.append(badge);

  const body = document.createElement("div");
  body.className = "product-card-body";
  const destination = document.createElement("p");
  destination.className = "product-destination";
  destination.textContent = product.destination;
  const title = document.createElement("h3");
  title.className = "product-name";
  title.textContent = product.name;
  const footer = document.createElement("div");
  footer.className = "product-card-footer";
  const priceBlock = document.createElement("div");
  const price = document.createElement("p");
  price.className = "product-price";
  price.textContent = money(product.base_price, product.currency);
  const stock = document.createElement("span");
  stock.className = "stock-label";
  stock.textContent = stockText(product);
  priceBlock.append(price, stock);
  const details = document.createElement("button");
  details.className = "button button-quiet card-details";
  details.type = "button";
  details.textContent = "Ver detalle";
  details.addEventListener("click", () => openDetails(product));
  footer.append(priceBlock, details);
  body.append(destination, title, footer);
  card.append(imageWrap, body);
  return card;
}

function openDetails(product) {
  state.detailProduct = product;
  state.detailImageIndex = 0;
  byId("detailType").textContent = TYPE_NAMES[product.product_type] || "Experiencia";
  byId("detailTitle").textContent = product.name;
  byId("detailDestination").textContent = product.destination;
  byId("detailSku").textContent = `Código: ${product.sku}`;
  byId("detailDescription").textContent = product.description || "Consultá para conocer más detalles de esta experiencia.";
  byId("detailPrice").textContent = money(product.base_price, product.currency);
  byId("detailStock").textContent = stockText(product);
  byId("detailQuantity").value = "1";
  const soldOut = product.availability_mode === "finite" && (product.available_units ?? 0) < 1;
  byId("detailQuantity").max = product.availability_mode === "finite" ? String(product.available_units ?? 0) : "100";
  byId("detailQuantity").disabled = soldOut;
  byId("addToCartButton").disabled = soldOut;
  byId("addToCartButton").textContent = soldOut ? "Sin disponibilidad" : "Agregar al carrito";
  const startDate = formatDate(product.starts_on);
  const endDate = formatDate(product.ends_on);
  byId("detailDates").textContent = startDate || endDate
    ? `Fechas: ${startDate || "A confirmar"}${endDate ? ` al ${endDate}` : ""}`
    : "Fechas a coordinar";
  const packageIncludes = product.package_components?.length
    ? product.package_components.map((item) => `${item.quantity > 1 ? `${item.quantity} × ` : ""}${item.name}`).join(" · ")
    : null;
  renderDetailFields(packageIncludes ? { ...(product.details || {}), incluye: packageIncludes } : product.details);
  const cancellation = product.cancellation_policy?.trim();
  byId("detailCancellationSection").hidden = !cancellation;
  byId("detailCancellation").textContent = cancellation || "";
  renderDetailImage();
  const dialog = byId("detailDialog");
  if (!dialog.open) dialog.showModal();
  history.replaceState(null, "", `${location.pathname}${location.search}#producto=${product.id}`);
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("es-AR", { dateStyle: "medium" }).format(date);
}

function renderDetailImage() {
  const product = state.detailProduct;
  const images = product?.images || [];
  const image = byId("detailImage");
  const hasImages = images.length > 0;
  image.hidden = !hasImages;
  image.src = hasImages ? imageUrl(images[state.detailImageIndex].url) : "";
  image.alt = hasImages ? (images[state.detailImageIndex].alt_text || product.name) : "";
  byId("detailImageCount").textContent = hasImages ? `${state.detailImageIndex + 1} / ${images.length}` : "Sin imágenes";
  byId("detailPrevious").hidden = images.length < 2;
  byId("detailNext").hidden = images.length < 2;
}

function changeDetailImage(direction) {
  const images = state.detailProduct?.images || [];
  if (images.length < 2) return;
  state.detailImageIndex = (state.detailImageIndex + direction + images.length) % images.length;
  renderDetailImage();
}

function renderDetailFields(details) {
  const section = byId("detailExtraSection");
  const list = byId("detailExtra");
  list.replaceChildren();
  const entries = details && typeof details === "object" && !Array.isArray(details) ? Object.entries(details) : [];
  section.hidden = entries.length === 0;
  for (const [key, value] of entries) {
    const term = document.createElement("dt");
    term.textContent = key.replaceAll("_", " ");
    const description = document.createElement("dd");
    if (value && typeof value === "object") {
      const nestedList = document.createElement(Array.isArray(value) ? "ul" : "span");
      if (Array.isArray(value)) {
        for (const item of value) {
          const listItem = document.createElement("li");
          listItem.textContent = typeof item === "object" ? JSON.stringify(item) : String(item);
          nestedList.append(listItem);
        }
      } else nestedList.textContent = Object.entries(value).map(([nestedKey, nestedValue]) => `${nestedKey}: ${typeof nestedValue === "object" ? JSON.stringify(nestedValue) : nestedValue}`).join(" · ");
      description.append(nestedList);
    } else description.textContent = value === null || value === undefined ? "—" : String(value);
    list.append(term, description);
  }
}

async function shareCurrentProduct() {
  const product = state.detailProduct;
  if (!product) return;
  const url = new URL(location.href);
  url.searchParams.delete("api");
  url.hash = `producto=${product.id}`;
  const shareData = { title: product.name, text: `${product.name} · ${product.destination}`, url: url.href };
  try {
    if (navigator.share) await navigator.share(shareData);
    else {
      await navigator.clipboard.writeText(url.href);
      showToast("Enlace copiado");
    }
  } catch (error) {
    if (error.name !== "AbortError") showToast("No se pudo compartir el enlace");
  }
}

function openCart() {
  if (state.role !== "customer") {
    if (state.token) showToast("El carrito está disponible para cuentas de cliente.");
    else byId("loginDialog").showModal();
    return;
  }
  location.href = "cart.html";
}

async function loadCart(showDialog = false) {
  if (state.role !== "customer") return;
  byId("cartMessage").textContent = "Cargando carrito…";
  try {
    state.cart = await api("/cart");
    renderCart();
    if (showDialog) location.href = "cart.html";
  } catch (error) {
    byId("cartMessage").textContent = error.message;
    if (error.status === 401) {
      clearSession();
      byId("loginDialog").showModal();
    }
  }
}

function renderCart() {
  const items = state.cart?.items || [];
  const container = byId("cartItems");
  container.replaceChildren();
  byId("cartEmpty").hidden = items.length > 0;
  byId("cartFooter").hidden = items.length === 0;
  byId("cartMessage").textContent = "";
  byId("cartExpiry").textContent = state.cart?.expires_at
    ? "Este carrito vence " + new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(new Date(state.cart.expires_at)) + "."
    : "";
  for (const item of items) container.append(makeCartItem(item));
  const totals = byId("cartTotals");
  totals.replaceChildren();
  for (const total of state.cart?.totals || []) {
    const amount = document.createElement("span");
    amount.textContent = money(total.amount, total.currency);
    totals.append(amount);
  }
  updateCartCount();
}

function makeCartItem(item) {
  const row = document.createElement("article");
  row.className = "cart-item";
  const image = document.createElement("img");
  image.className = "cart-item-image";
  if (item.image_url) {
    image.src = imageUrl(item.image_url);
    image.alt = "";
    image.onerror = () => { image.hidden = true; };
  } else image.hidden = true;

  const info = document.createElement("div");
  info.className = "cart-item-info";
  const title = document.createElement("h3");
  title.textContent = item.product_name;
  const destination = document.createElement("p");
  destination.textContent = item.destination;
  const price = document.createElement("p");
  price.textContent = money(item.unit_price, item.currency) + " c/u";
  info.append(title, destination, price);

  const controls = document.createElement("div");
  controls.className = "cart-item-controls";
  const decrement = document.createElement("button");
  decrement.className = "button button-quiet";
  decrement.type = "button";
  decrement.setAttribute("aria-label", "Quitar una unidad de " + item.product_name);
  decrement.textContent = "−";
  decrement.addEventListener("click", () => updateCartItem(item, item.quantity - 1));
  const quantity = document.createElement("span");
  quantity.textContent = String(item.quantity);
  const increment = document.createElement("button");
  increment.className = "button button-quiet";
  increment.type = "button";
  increment.setAttribute("aria-label", "Agregar una unidad de " + item.product_name);
  increment.textContent = "+";
  increment.disabled = item.availability_mode === "finite" && item.quantity >= (item.available_units ?? 0);
  increment.addEventListener("click", () => updateCartItem(item, item.quantity + 1));
  const remove = document.createElement("button");
  remove.className = "text-button";
  remove.type = "button";
  remove.textContent = "Quitar";
  remove.addEventListener("click", () => removeCartItem(item.id));
  controls.append(decrement, quantity, increment, remove);
  const lineTotal = document.createElement("strong");
  lineTotal.className = "cart-line-total";
  lineTotal.textContent = money(item.line_total, item.currency);
  row.append(image, info, controls, lineTotal);
  return row;
}

async function updateCartItem(item, quantity) {
  if (quantity < 1) return removeCartItem(item.id);
  try {
    state.cart = await api("/cart/items/" + item.id, { method: "PATCH", body: JSON.stringify({ quantity }) });
    renderCart();
  } catch (error) { byId("cartMessage").textContent = error.message; }
}

async function removeCartItem(itemId) {
  try {
    state.cart = await api("/cart/items/" + itemId, { method: "DELETE" });
    renderCart();
  } catch (error) { byId("cartMessage").textContent = error.message; }
}

async function clearCart() {
  if (!state.cart?.items?.length || !window.confirm("¿Querés quitar todos los productos del carrito?")) return;
  try {
    state.cart = await api("/cart", { method: "DELETE" });
    renderCart();
    showToast("Carrito vaciado");
  } catch (error) { byId("cartMessage").textContent = error.message; }
}

async function addProductToCart() {
  const product = state.detailProduct;
  if (!product) return;
  const quantity = Number(byId("detailQuantity").value);
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 100) {
    showToast("Ingresá una cantidad entre 1 y 100.");
    return;
  }
  if (product.availability_mode === "finite" && quantity > product.available_units) {
    showToast("Solo quedan " + product.available_units + " unidades disponibles.");
    return;
  }
  const item = { product_id: product.id, quantity };
  if (!state.token) {
    state.pendingCartItem = item;
    byId("loginDialog").showModal();
    return;
  }
  if (state.role !== "customer") {
    showToast("Iniciá sesión con una cuenta de cliente para usar el carrito.");
    return;
  }
  await submitPendingCartItem(item);
}

async function submitPendingCartItem(item) {
  try {
    state.cart = await api("/cart/items", { method: "POST", body: JSON.stringify(item) });
    state.pendingCartItem = null;
    updateCartCount();
    if (byId("detailDialog").open) byId("detailDialog").close();
    location.href = "cart.html";
    showToast("Producto agregado al carrito");
  } catch (error) { showToast(error.message); }
}

async function finishAuthentication(token) {
  setSession(token);
  byId("loginDialog").close();
  byId("signupDialog").close();
  if (state.role === "sales_manager") {
    setView("admin");
    return;
  }
  setView("store");
  if (state.role === "customer") {
    await loadCart(false);
    if (state.pendingCartItem) await submitPendingCartItem(state.pendingCartItem);
    else showToast("Sesión iniciada");
    return;
  }
  showToast("Esta cuenta no tiene acceso al carrito.");
}

async function loadCatalog() {
  byId("catalogStatus").textContent = "Cargando experiencias…";
  try {
    state.products = await api("/catalog/products");
    byId("catalogStatus").textContent = state.products.length ? `${state.products.length} experiencias para descubrir` : "Todavía no hay productos publicados.";
    renderProducts();
    const requestedId = new URLSearchParams(location.hash.slice(1)).get("producto");
    if (requestedId && !byId("detailDialog").open) {
      const product = state.products.find((item) => String(item.id) === requestedId);
      if (product) openDetails(product);
    }
  } catch (error) {
    byId("catalogStatus").textContent = `No pudimos conectar con el catálogo: ${error.message}. Revisá que el backend esté iniciado.`;
  }
}

function setView(view) {
  const isAdmin = view === "admin";
  storeView.hidden = isAdmin;
  adminView.hidden = !isAdmin;
  byId("homeNav").classList.toggle("is-active", !isAdmin);
  byId("manageNav").classList.toggle("is-active", isAdmin);
  if (isAdmin) loadAdminProducts();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadAdminProducts() {
  byId("adminStatus").textContent = "Cargando productos…";
  try {
    const products = await api("/catalog/products/manage/all");
    byId("adminStatus").textContent = `${products.length} productos en el catálogo`;
    const container = byId("adminProducts");
    container.replaceChildren();
    for (const product of products) container.append(makeAdminCard(product));
  } catch (error) {
    byId("adminStatus").textContent = error.message;
    if (error.status === 401) {
      clearSession();
      byId("adminStatus").textContent = "La sesión venció. Ingresá nuevamente.";
      openLogin();
    } else if (error.status === 403 && !state.token) openLogin();
    else if (error.status === 403) byId("adminStatus").textContent = "Tu cuenta no tiene permisos para administrar el catálogo.";
  }
}

function makeAdminCard(product) {
  const card = document.createElement("article");
  card.className = `admin-card${product.is_active ? "" : " product-inactive"}`;
  const thumb = document.createElement("div");
  thumb.className = "admin-thumb";
  if (product.images?.[0]) {
    const image = document.createElement("img");
    image.src = imageUrl(product.images[0].url);
    image.alt = product.images[0].alt_text || "";
    image.onerror = () => image.remove();
    thumb.append(image);
  }
  const info = document.createElement("div");
  info.className = "admin-card-info";
  const title = document.createElement("h3");
  title.textContent = product.name;
  const meta = document.createElement("p");
  meta.className = "admin-meta";
  meta.textContent = `${product.sku} · ${product.destination} · ${product.is_active ? "Publicado" : "Desactivado"}`;
  info.append(title, meta);
  const actions = document.createElement("div");
  actions.className = "admin-card-actions";
  const edit = document.createElement("button");
  edit.type = "button";
  edit.className = "button button-quiet";
  edit.textContent = "Editar";
  edit.addEventListener("click", () => openProductForm(product));
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = `button ${product.is_active ? "button-danger" : "button-success"}`;
  toggle.textContent = product.is_active ? "Desactivar" : "Reactivar";
  toggle.addEventListener("click", () => toggleProduct(product));
  actions.append(edit, toggle);
  card.append(thumb, info, actions);
  return card;
}

function openLogin() {
  byId("loginMessage").textContent = "";
  byId("loginDialog").showModal();
}

function logout() {
  clearSession();
  state.pendingCartItem = null;
  setView("store");
  showToast("Sesión cerrada");
}

function openProductForm(product = null) {
  state.currentProduct = product;
  byId("productForm").reset();
  byId("productMessage").textContent = "";
  byId("productId").value = product?.id || "";
  byId("productDialogTitle").textContent = product ? "Editar producto" : "Nuevo producto";
  byId("productName").value = product?.name || "";
  byId("productSku").value = product?.sku || "";
  byId("productType").value = product?.product_type || "accommodation";
  populatePackageComponents(product);
  byId("productDestination").value = product?.destination || "";
  byId("productPrice").value = product?.base_price ?? "";
  byId("productCurrency").value = product?.currency || "ARS";
  byId("productAvailability").value = product?.availability_mode || "finite";
  byId("productStock").value = product?.available_units ?? "0";
  byId("productStarts").value = product?.starts_on || "";
  byId("productEnds").value = product?.ends_on || "";
  byId("productDescription").value = product?.description || "";
  byId("productDetails").value = product?.details ? JSON.stringify(product.details, null, 2) : "";
  byId("productCancellation").value = product?.cancellation_policy || "";
  byId("productImageAlt").value = "";
  setStockField();
  setPackageComponentsField();
  renderExistingImages(product?.images || []);
  productDialog.showModal();
}

function setStockField() {
  const unlimited = byId("productAvailability").value === "unlimited";
  byId("stockField").hidden = unlimited;
  byId("productStock").required = !unlimited;
}

function populatePackageComponents(product = null) {
  const select = byId("packageComponents");
  select.replaceChildren();
  const selected = new Set((product?.package_components || []).map((item) => String(item.product_id)));
  for (const item of state.products.filter((entry) => entry.product_type !== "package" && entry.is_active !== false)) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = `${item.name} · ${item.destination}`;
    option.selected = selected.has(String(item.id));
    select.append(option);
  }
}

function setPackageComponentsField() {
  const isPackage = byId("productType").value === "package";
  byId("packageComponentsField").hidden = !isPackage;
  byId("packageComponents").required = isPackage;
}

function renderExistingImages(images) {
  const container = byId("existingImages");
  container.replaceChildren();
  if (!images.length) return;
  const heading = document.createElement("span");
  heading.textContent = "Imágenes cargadas";
  container.append(heading);
  const list = document.createElement("div");
  list.className = "existing-image-list";
  for (const image of images) {
    const item = document.createElement("div");
    item.className = "existing-image-item";
    const thumb = document.createElement("img");
    thumb.src = imageUrl(image.url);
    thumb.alt = image.alt_text || "Imagen del producto";
    const remove = document.createElement("button");
    remove.className = "button button-danger";
    remove.type = "button";
    remove.textContent = "Quitar";
    remove.addEventListener("click", async () => {
      try {
        await api(`/catalog/products/${state.currentProduct.id}/images/${image.id}`, { method: "DELETE" });
        state.currentProduct.images = state.currentProduct.images.filter((entry) => entry.id !== image.id);
        renderExistingImages(state.currentProduct.images);
        showToast("Imagen eliminada");
      } catch (error) { byId("productMessage").textContent = error.message; }
    });
    item.append(thumb, remove);
    list.append(item);
  }
  container.append(list);
}

async function toggleProduct(product) {
  const action = product.is_active ? "desactivar" : "reactivar";
  if (!window.confirm(`¿Querés ${action} “${product.name}”?`)) return;
  try {
    await api(`/catalog/products/${product.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !product.is_active }) });
    showToast(product.is_active ? "Producto desactivado" : "Producto reactivado");
    await loadAdminProducts();
    await loadCatalog();
  } catch (error) { showToast(error.message); }
}

function productPayload() {
  const availability = byId("productAvailability").value;
  const rawDetails = byId("productDetails").value.trim();
  let details = null;
  if (rawDetails) {
    try { details = JSON.parse(rawDetails); }
    catch { throw new Error("Los detalles adicionales deben ser JSON válido."); }
    if (!details || Array.isArray(details) || typeof details !== "object") throw new Error("Los detalles deben ser un objeto JSON.");
  }
  const isPackage = byId("productType").value === "package";
  const package_components = isPackage ? [...byId("packageComponents").selectedOptions].map((option) => ({ product_id: Number(option.value), quantity: 1 })) : [];
  return {
    sku: byId("productSku").value.trim(),
    name: byId("productName").value.trim(),
    product_type: byId("productType").value,
    destination: byId("productDestination").value.trim(),
    description: byId("productDescription").value.trim() || null,
    cancellation_policy: byId("productCancellation").value.trim() || null,
    details,
    base_price: byId("productPrice").value,
    currency: byId("productCurrency").value,
    availability_mode: availability,
    available_units: availability === "unlimited" ? null : Number(byId("productStock").value),
    starts_on: byId("productStarts").value || null,
    ends_on: byId("productEnds").value || null,
    is_active: state.currentProduct?.is_active ?? true,
    package_components,
  };
}

async function uploadSelectedImages(productId) {
  const files = [...byId("productImages").files];
  for (const file of files) {
    const form = new FormData();
    form.append("file", file);
    const altText = byId("productImageAlt").value.trim();
    if (altText) form.append("alt_text", altText);
    await api(`/catalog/products/${productId}/images`, { method: "POST", body: form });
  }
}

async function saveProduct(event) {
  event.preventDefault();
  const message = byId("productMessage");
  message.textContent = "Guardando…";
  const id = byId("productId").value;
  const method = id ? "PATCH" : "POST";
  const path = id ? `/catalog/products/${id}` : "/catalog/products";
  try {
    const product = await api(path, { method, body: JSON.stringify(productPayload()) });
    let imageError = null;
    try { await uploadSelectedImages(product.id); }
    catch (error) { imageError = error; }
    productDialog.close();
    showToast(imageError
      ? `Producto guardado; no se cargaron todas las imágenes: ${imageError.message}`
      : (id ? "Producto actualizado" : "Producto creado"));
    await loadAdminProducts();
    await loadCatalog();
  } catch (error) {
    message.textContent = error.message;
  }
}

byId("searchForm").addEventListener("submit", (event) => {
  event.preventDefault();
  state.query = byId("searchInput").value;
  renderProducts();
  const visibleCount = productGrid.childElementCount;
  byId("catalogStatus").textContent = `${visibleCount} ${visibleCount === 1 ? "resultado" : "resultados"}`;
});
byId("searchInput").addEventListener("input", (event) => { state.query = event.target.value; renderProducts(); });
byId("refreshButton").addEventListener("click", loadCatalog);
byId("refreshAdminButton").addEventListener("click", loadAdminProducts);
document.querySelectorAll(".category-chip").forEach((chip) => chip.addEventListener("click", () => {
  document.querySelector(".category-chip.is-selected")?.classList.remove("is-selected");
  chip.classList.add("is-selected");
  state.filter = chip.dataset.category;
  renderProducts();
}));
byId("accountButton").addEventListener("click", () => {
  if (!state.token) openLogin();
  else if (state.role === "customer") location.assign("profile.html");
  else logout();
});
byId("adminTopButton").addEventListener("click", () => setView("admin"));
byId("manageNav").addEventListener("click", () => {
  if (state.role === "sales_manager") setView("admin");
  else if (!state.token) openLogin();
});
byId("cartButton").addEventListener("click", (event) => {
  if (state.role !== "customer") { event.preventDefault(); openCart(); }
});
byId("addToCartButton").addEventListener("click", addProductToCart);
byId("homeNav").addEventListener("click", () => setView("store"));
document.querySelector(".brand").addEventListener("click", () => setView("store"));
byId("newProductButton").addEventListener("click", () => openProductForm());
byId("productAvailability").addEventListener("change", setStockField);
byId("productType").addEventListener("change", () => { populatePackageComponents(state.currentProduct); setPackageComponentsField(); });
byId("productForm").addEventListener("submit", saveProduct);
byId("detailPrevious").addEventListener("click", () => changeDetailImage(-1));
byId("detailNext").addEventListener("click", () => changeDetailImage(1));
byId("shareProductButton").addEventListener("click", shareCurrentProduct);
byId("detailDialog").addEventListener("close", () => {
  if (location.hash.startsWith("#producto=")) history.replaceState(null, "", `${location.pathname}${location.search}`);
});
byId("detailDialog").addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") changeDetailImage(-1);
  if (event.key === "ArrowRight") changeDetailImage(1);
});
byId("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = byId("loginMessage");
  message.textContent = "Ingresando…";
  const form = new FormData(event.currentTarget);
  try {
    const result = await api("/auth/login", { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) });
    await finishAuthentication(result.access_token);
  } catch (error) { message.textContent = error.message; }
});
byId("openSignupButton").addEventListener("click", () => {
  byId("loginDialog").close();
  byId("signupMessage").textContent = "";
  byId("signupDialog").showModal();
});
byId("openLoginButton").addEventListener("click", () => {
  byId("signupDialog").close();
  openLogin();
});
byId("signupForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = byId("signupMessage");
  message.textContent = "Creando cuenta…";
  const form = new FormData(event.currentTarget);
  const data = Object.fromEntries(form.entries());
  if (!data.phone) data.phone = null;
  try {
    const result = await api("/auth/register/customer", { method: "POST", body: JSON.stringify(data) });
    await finishAuthentication(result.access_token);
    event.currentTarget.reset();
  } catch (error) { message.textContent = error.message; }
});
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => byId(button.dataset.close).close()));
byId("accountButton").textContent = state.token ? (state.role === "customer" ? "Mi perfil" : "Salir") : "Ingresar";
byId("manageNav").hidden = state.role !== "sales_manager";
byId("adminTopButton").hidden = state.role !== "sales_manager";
if (state.role === "customer") loadCart(false);
loadCatalog();
