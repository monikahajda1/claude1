'use strict';

const STORAGE_KEY = 'todo-app-v1';
const ALL = 'all';

const PRIORITY_LABELS = { low: 'Niski', medium: 'Średni', high: 'Wysoki' };
const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };

const DEFAULT_STATE = {
  categories: [
    { id: 'c-dom', name: 'Dom', color: '#30a46c' },
    { id: 'c-praca', name: 'Praca', color: '#4f7cff' },
    { id: 'c-zakupy', name: 'Zakupy', color: '#f5a524' },
  ],
  tasks: [],
};

let state = load();
let currentCategory = ALL;
let currentStatus = 'all';
let searchQuery = '';

// ---------- Persistence ----------

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed.categories) && Array.isArray(parsed.tasks)) return parsed;
    }
  } catch (e) {
    console.warn('Nie udało się wczytać danych:', e);
  }
  return structuredClone(DEFAULT_STATE);
}

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('Nie udało się zapisać danych:', e);
  }
}

function uid(prefix) {
  return prefix + '-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

// ---------- Helpers ----------

const $ = (sel) => document.querySelector(sel);

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') node.className = v;
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else if (k in node) node[k] = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

function getCategory(id) {
  return state.categories.find((c) => c.id === id);
}

function todayISO() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

function formatDate(iso) {
  const [y, m, d] = iso.split('-');
  return `${d}.${m}.${y}`;
}

// ---------- Rendering ----------

function render() {
  renderCategories();
  renderCategorySelect();
  renderTasks();
}

function renderCategories() {
  const list = $('#category-list');
  list.replaceChildren();

  const countOpen = (catId) =>
    state.tasks.filter((t) => !t.done && (catId === ALL || t.categoryId === catId)).length;

  list.append(
    el('li', {
      class: currentCategory === ALL ? 'active' : '',
      onclick: () => selectCategory(ALL),
    },
      el('span', { class: 'dot', style: 'background: var(--muted)' }),
      el('span', { class: 'name', textContent: 'Wszystkie' }),
      el('span', { class: 'count', textContent: countOpen(ALL) }),
    ),
  );

  for (const cat of state.categories) {
    list.append(
      el('li', {
        class: currentCategory === cat.id ? 'active' : '',
        onclick: () => selectCategory(cat.id),
        ondblclick: () => renameCategory(cat.id),
        title: 'Kliknij dwukrotnie, aby zmienić nazwę',
      },
        el('span', { class: 'dot', style: `background:${cat.color}` }),
        el('span', { class: 'name', textContent: cat.name }),
        el('span', { class: 'count', textContent: countOpen(cat.id) }),
        el('button', {
          class: 'icon-btn',
          title: 'Usuń kategorię',
          textContent: '✕',
          onclick: (e) => { e.stopPropagation(); deleteCategory(cat.id); },
        }),
      ),
    );
  }
}

function renderCategorySelect() {
  const select = $('#task-category');
  const previous = select.value;
  select.replaceChildren(
    ...state.categories.map((c) => el('option', { value: c.id, textContent: c.name })),
  );
  if (currentCategory !== ALL) select.value = currentCategory;
  else if (getCategory(previous)) select.value = previous;
  select.disabled = state.categories.length === 0;
}

function visibleTasks() {
  const q = searchQuery.trim().toLowerCase();
  return state.tasks
    .filter((t) => currentCategory === ALL || t.categoryId === currentCategory)
    .filter((t) => currentStatus === 'all' || (currentStatus === 'done' ? t.done : !t.done))
    .filter((t) => !q || t.title.toLowerCase().includes(q))
    .sort((a, b) =>
      (a.done - b.done) ||
      ((a.due || '9999') .localeCompare(b.due || '9999')) ||
      (PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]) ||
      (a.createdAt - b.createdAt),
    );
}

function renderTasks() {
  const cat = getCategory(currentCategory);
  $('#view-title').textContent = cat ? cat.name : 'Wszystkie';

  const tasks = visibleTasks();
  const list = $('#task-list');
  list.replaceChildren(...tasks.map(renderTask));
  $('#empty').hidden = tasks.length > 0;

  const scope = state.tasks.filter((t) => currentCategory === ALL || t.categoryId === currentCategory);
  const done = scope.filter((t) => t.done).length;
  $('#counter').textContent = scope.length ? `${done} / ${scope.length} zrobione` : '';
}

function renderTask(task) {
  const cat = getCategory(task.categoryId);
  const overdue = task.due && !task.done && task.due < todayISO();

  const meta = el('div', { class: 'meta' });
  if (currentCategory === ALL && cat) {
    meta.append(el('span', { class: 'tag' },
      el('span', { class: 'dot', style: `background:${cat.color}` }), cat.name));
  }
  meta.append(el('span', { textContent: `Priorytet: ${PRIORITY_LABELS[task.priority]}` }));
  if (task.due) {
    meta.append(el('span', {
      class: overdue ? 'overdue' : '',
      textContent: (overdue ? 'Po terminie: ' : 'Termin: ') + formatDate(task.due),
    }));
  }

  const title = el('div', { class: 'title', textContent: task.title });

  return el('li', { class: `task priority-${task.priority}${task.done ? ' done' : ''}` },
    el('input', {
      type: 'checkbox',
      checked: task.done,
      title: 'Oznacz jako zrobione',
      onchange: () => toggleTask(task.id),
    }),
    el('div', { class: 'body' }, title, meta),
    el('div', { class: 'actions' },
      el('button', { title: 'Edytuj', textContent: '✎', onclick: () => editTask(task.id, title) }),
      el('button', { class: 'delete', title: 'Usuń', textContent: '🗑', onclick: () => deleteTask(task.id) }),
    ),
  );
}

// ---------- Actions ----------

function selectCategory(id) {
  currentCategory = id;
  render();
}

function addCategory(name, color) {
  name = name.trim();
  if (!name) return;
  if (state.categories.some((c) => c.name.toLowerCase() === name.toLowerCase())) {
    alert('Kategoria o tej nazwie już istnieje.');
    return;
  }
  const cat = { id: uid('c'), name, color };
  state.categories.push(cat);
  currentCategory = cat.id;
  save();
  render();
}

function renameCategory(id) {
  const cat = getCategory(id);
  const name = prompt('Nowa nazwa kategorii:', cat.name);
  if (name && name.trim()) {
    cat.name = name.trim();
    save();
    render();
  }
}

function deleteCategory(id) {
  const cat = getCategory(id);
  const count = state.tasks.filter((t) => t.categoryId === id).length;
  const msg = count
    ? `Usunąć kategorię „${cat.name}” razem z ${count} zadaniami?`
    : `Usunąć kategorię „${cat.name}”?`;
  if (!confirm(msg)) return;
  state.categories = state.categories.filter((c) => c.id !== id);
  state.tasks = state.tasks.filter((t) => t.categoryId !== id);
  if (currentCategory === id) currentCategory = ALL;
  save();
  render();
}

function addTask({ title, categoryId, priority, due }) {
  title = title.trim();
  if (!title || !getCategory(categoryId)) return;
  state.tasks.push({
    id: uid('t'),
    title,
    categoryId,
    priority,
    due: due || null,
    done: false,
    createdAt: Date.now(),
  });
  save();
  render();
}

function toggleTask(id) {
  const task = state.tasks.find((t) => t.id === id);
  task.done = !task.done;
  save();
  render();
}

function editTask(id, titleNode) {
  const task = state.tasks.find((t) => t.id === id);
  const input = el('input', { class: 'title-edit', value: task.title, maxLength: 200 });
  let finished = false;
  const finish = (commit) => {
    if (finished) return;
    finished = true;
    if (commit && input.value.trim()) {
      task.title = input.value.trim();
      save();
    }
    render();
  };
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') finish(true);
    if (e.key === 'Escape') finish(false);
  });
  input.addEventListener('blur', () => finish(true));
  titleNode.replaceWith(input);
  input.focus();
  input.select();
}

function deleteTask(id) {
  state.tasks = state.tasks.filter((t) => t.id !== id);
  save();
  render();
}

function clearDone() {
  const scope = (t) => currentCategory === ALL || t.categoryId === currentCategory;
  const n = state.tasks.filter((t) => t.done && scope(t)).length;
  if (!n || !confirm(`Usunąć ${n} zrobionych zadań?`)) return;
  state.tasks = state.tasks.filter((t) => !(t.done && scope(t)));
  save();
  render();
}

// ---------- Events ----------

$('#category-form').addEventListener('submit', (e) => {
  e.preventDefault();
  addCategory($('#category-name').value, $('#category-color').value);
  $('#category-name').value = '';
});

$('#task-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (!state.categories.length) {
    alert('Najpierw dodaj kategorię.');
    return;
  }
  addTask({
    title: $('#task-title').value,
    categoryId: $('#task-category').value,
    priority: $('#task-priority').value,
    due: $('#task-due').value,
  });
  $('#task-title').value = '';
  $('#task-due').value = '';
  $('#task-title').focus();
});

$('#search').addEventListener('input', (e) => {
  searchQuery = e.target.value;
  renderTasks();
});

document.querySelectorAll('.filters button').forEach((btn) => {
  btn.addEventListener('click', () => {
    currentStatus = btn.dataset.status;
    document.querySelectorAll('.filters button').forEach((b) => b.classList.toggle('active', b === btn));
    renderTasks();
  });
});

$('#clear-done').addEventListener('click', clearDone);

render();
