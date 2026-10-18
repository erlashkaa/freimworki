"use strict";
const $ = (selector) => document.querySelector(selector);
const state = {csrf: "", register: false, page: 1, categories: [], load: 0};
const rubles = (value) => new Intl.NumberFormat("ru-RU", {style: "currency", currency: "RUB"}).format(Number(value));
const today = new Date();
const localDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
$("#month").value = localDate.slice(0, 7);
$("[name=date]").value = localDate;

function notify(message, failure = false) {
  $("#notice").textContent = message;
  $("#notice").classList.toggle("error", failure);
}

async function api(path, method = "GET", data) {
  const options = {method, credentials: "same-origin", headers: {"X-CSRFToken": state.csrf}};
  if (data !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(data);
  }
  const response = await fetch(`/api/${path}`, options);
  const body = await response.json().catch(() => ({error: "Сервер вернул некорректный ответ"}));
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("login")) showUser(null);
    const fields = Object.values(body.fields || {}).flat().join(" ");
    throw new Error(fields || body.error || "Не удалось выполнить запрос");
  }
  if (body.csrfToken) state.csrf = body.csrfToken;
  return body;
}

function showUser(user) {
  state.load++;
  $("#auth").hidden = Boolean(user);
  $("#dashboard").hidden = !user;
  $("#account").hidden = !user;
  $("#username").textContent = user ? user.username : "";
  if (!user) {
    $("#transactions").replaceChildren();
    $("#limits").replaceChildren();
    state.categories = [];
    state.page = 1;
    fillSelect("#filter", [], "Все категории");
    fillSelect("#category-select", [], "Выберите категорию");
    $("#transaction-form").reset();
    $("[name=date]").value = localDate;
    resetCategory();
  }
}

function fillSelect(selector, categories, label) {
  const element = $(selector);
  const old = element.value;
  element.replaceChildren(new Option(label, ""));
  categories.forEach((c) => element.add(new Option(c.name, String(c.id))));
  if (categories.some((c) => String(c.id) === old)) element.value = old;
}

async function refresh() {
  const load = ++state.load;
  const month = $("#month").value;
  const query = new URLSearchParams({month, page: state.page, category: $("#filter").value, ordering: $("#ordering").value});
  const [summary, categories, history] = await Promise.all([
    api(`summary/?month=${encodeURIComponent(month)}`), api("categories/"), api(`transactions/?${query}`),
  ]);
  if (load !== state.load) return;
  state.categories = categories.results;
  $("#balance").textContent = rubles(summary.balance);
  $("#income").textContent = rubles(summary.income);
  $("#expense").textContent = rubles(summary.expense);
  fillSelect("#category-select", categories.results, "Выберите категорию");
  fillSelect("#filter", categories.results, "Все категории");
  $("#add-transaction").disabled = categories.results.length === 0;
  $("#category-hint").hidden = categories.results.length > 0;
  $("#limits").replaceChildren();
  if (!summary.categories.length) $("#limits").textContent = "Категории пока не добавлены.";
  summary.categories.forEach((c) => {
    const row = document.createElement("div");
    row.className = "limit-row" + (Number(c.remaining) < 0 ? " over" : "");
    const text = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = c.name;
    const details = document.createElement("span");
    details.textContent = `Потрачено ${rubles(c.spent)} · ` + (c.limit === null ? "без лимита" : `лимит ${rubles(c.limit)} · ${Number(c.remaining) < 0 ? "превышение" : "остаток"} ${rubles(Math.abs(Number(c.remaining)))}`);
    text.append(name, details);
    const edit = document.createElement("button");
    edit.className = "secondary";
    edit.textContent = "Изменить";
    edit.addEventListener("click", () => editCategory(c));
    row.append(text, edit);
    $("#limits").append(row);
  });
  $("#transactions").replaceChildren();
  history.results.forEach((item) => {
    const row = document.createElement("tr");
    if (item.is_cancelled) row.className = "cancelled";
    const values = [item.date.split("-").reverse().join("."), item.category_name, item.description || "—", `${item.type === "income" ? "+" : "−"}${rubles(item.amount)}`, item.is_cancelled ? "Отменена" : "Активна"];
    values.forEach((value, i) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (i === 3 && item.type === "income" && !item.is_cancelled) cell.className = "income";
      row.append(cell);
    });
    const action = document.createElement("td");
    if (!item.is_cancelled) {
      const button = document.createElement("button");
      button.className = "secondary";
      button.textContent = "Отменить";
      button.addEventListener("click", () => perform(button, async () => {
        await api(`transactions/${item.id}/cancel/`, "POST", {});
        await refresh();
        notify("Операция отменена. Баланс обновлён.");
      }));
      action.append(button);
    }
    row.append(action);
    $("#transactions").append(row);
  });
  $("#empty").hidden = history.results.length > 0;
  $("#previous").disabled = state.page <= 1;
  $("#next").disabled = state.page * history.page_size >= history.count;
  $("#page-label").textContent = `Страница ${state.page} · операций: ${history.count}`;
}

async function perform(button, action) {
  button.disabled = true;
  try { await action(); } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; }
}

$("#auth-toggle").addEventListener("click", () => {
  state.register = !state.register;
  $("#auth-title").textContent = state.register ? "Создать аккаунт" : "Вход в аккаунт";
  $("#auth-submit").textContent = state.register ? "Зарегистрироваться" : "Войти";
  $("#auth-toggle").textContent = state.register ? "Уже есть аккаунт" : "Создать аккаунт";
  $("#repeat-label").hidden = !state.register;
  $("#password-hint").hidden = !state.register;
  $("[name=repeat]").required = state.register;
  $("[name=password]").autocomplete = state.register ? "new-password" : "current-password";
  notify("");
});

$("#auth-form").addEventListener("submit", (event) => {
  event.preventDefault();
  perform($("#auth-submit"), async () => {
    const data = Object.fromEntries(new FormData(event.target));
    const payload = state.register ? {username: data.username, password1: data.password, password2: data.repeat} : {username: data.username, password: data.password};
    const result = await api(state.register ? "register/" : "login/", "POST", payload);
    event.target.reset();
    showUser(result.user);
    await refresh();
    notify("Вы вошли в аккаунт.");
  });
});

$("#logout").addEventListener("click", () => perform($("#logout"), async () => {
  await api("logout/", "POST", {});
  showUser(null);
  $("#transaction-form").reset();
  $("[name=date]").value = localDate;
  resetCategory();
  notify("Вы вышли из аккаунта.");
}));

$("#transaction-form").addEventListener("submit", (event) => {
  event.preventDefault();
  perform($("#add-transaction"), async () => {
    const data = Object.fromEntries(new FormData(event.target));
    await api("transactions/", "POST", data);
    event.target.elements.amount.value = "";
    event.target.elements.description.value = "";
    $("#month").value = data.date.slice(0, 7);
    $("#filter").value = "";
    state.page = 1;
    await refresh();
    notify("Операция сохранена.");
  });
});

function editCategory(category) {
  const form = $("#category-form");
  form.elements.id.value = category.id;
  form.elements.name.value = category.name;
  form.elements.limit.value = category.limit ?? "";
  $("#category-title").textContent = "Изменить категорию";
  $("#category-reset").hidden = false;
  form.elements.name.focus();
}

function resetCategory() {
  $("#category-form").reset();
  $("#category-form").elements.id.value = "";
  $("#category-title").textContent = "Новая категория";
  $("#category-reset").hidden = true;
}

$("#category-reset").addEventListener("click", resetCategory);
$("#category-form").addEventListener("submit", (event) => {
  event.preventDefault();
  perform(event.target.querySelector("[type=submit]"), async () => {
    const data = Object.fromEntries(new FormData(event.target));
    await api(data.id ? `categories/${data.id}/` : "categories/", data.id ? "PATCH" : "POST", {name: data.name, limit: data.limit || null});
    resetCategory();
    await refresh();
    notify("Категория сохранена.");
  });
});

["#month", "#filter", "#ordering"].forEach((selector) => $(selector).addEventListener("change", () => {
  state.page = 1;
  refresh().catch((e) => notify(e.message, true));
}));
$("#previous").addEventListener("click", () => { state.page--; refresh().catch((e) => notify(e.message, true)); });
$("#next").addEventListener("click", () => { state.page++; refresh().catch((e) => notify(e.message, true)); });
api("session/").then(async (result) => { showUser(result.user); if (result.user) await refresh(); }).catch((e) => notify(e.message, true));
