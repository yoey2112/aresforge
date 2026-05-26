export function byId(id) {
  return document.getElementById(id);
}

export function on(id, eventName, handler) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.addEventListener(eventName, handler);
}

export function setMessage(id, text, tone) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.className = "message";
  element.textContent = text || "";
  if (tone) {
    element.classList.add(`message-${tone}`);
  }
}

export function setList(listId, emptyId, values) {
  const list = byId(listId);
  const empty = byId(emptyId);
  if (!list || !empty) {
    return;
  }
  list.innerHTML = "";
  if (!values || values.length === 0) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  });
}

export function setCodeBlock(blockId, emptyId, value) {
  const block = byId(blockId);
  const empty = byId(emptyId);
  if (!block || !empty) {
    return;
  }
  if (!value) {
    block.textContent = "";
    empty.style.display = "block";
    return;
  }
  block.textContent = value;
  empty.style.display = "none";
}

export function setText(id, value) {
  const element = byId(id);
  if (!element) {
    return;
  }
  element.textContent = String(value || "");
}