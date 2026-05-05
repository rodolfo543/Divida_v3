(function () {
  const API_URL = "/api/chat";
  const MAX_HISTORY = 10;
  const INITIAL_MESSAGE = "Oie :) Sou o Assistente AXS. Posso ajudar com contratos, emissoes de divida e conceitos financeiros. Sou uma IA e posso cometer erros; para informacoes oficiais, acesse https://ri.axsenergia.com.br";

  let history = [];
  let loading = false;

  const style = document.createElement("style");
  style.textContent = `
    #axs-chat-btn {
      position: fixed;
      right: 26px;
      bottom: 24px;
      width: 58px;
      height: 58px;
      border: 0;
      border-radius: 50%;
      background: #125a94;
      color: #fff;
      display: grid;
      place-items: center;
      cursor: pointer;
      box-shadow: 0 18px 34px rgba(0,0,0,0.34);
      z-index: 10000;
      transition: transform 180ms ease, background 180ms ease;
    }

    #axs-chat-btn:hover {
      transform: translateY(-2px) scale(1.04);
      background: #176aa9;
    }

    #axs-chat-btn svg {
      width: 30px;
      height: 30px;
    }

    #axs-chat-box {
      position: fixed;
      right: 26px;
      bottom: 94px;
      width: min(380px, calc(100vw - 24px));
      height: min(620px, calc(100vh - 110px));
      display: flex;
      flex-direction: column;
      background: #f3f6fa;
      border: 1px solid rgba(255,255,255,0.28);
      border-radius: 12px;
      box-shadow: 0 24px 70px rgba(0,0,0,0.36);
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
      transform: translateY(14px);
      transition: opacity 180ms ease, transform 180ms ease;
      z-index: 10001;
      font-family: Manrope, system-ui, sans-serif;
    }

    #axs-chat-box.open {
      opacity: 1;
      pointer-events: all;
      transform: translateY(0);
    }

    #axs-chat-header {
      flex: 0 0 auto;
      height: 56px;
      padding: 10px 14px;
      background: #13598f;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: move;
      user-select: none;
    }

    #axs-chat-header img {
      width: 36px;
      height: 36px;
      object-fit: contain;
      flex: 0 0 auto;
    }

    #axs-chat-title {
      min-width: 0;
      line-height: 1.15;
    }

    #axs-chat-title strong,
    #axs-chat-title small {
      display: block;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    #axs-chat-title strong {
      font-size: 0.92rem;
      font-weight: 800;
    }

    #axs-chat-title small {
      margin-top: 2px;
      font-size: 0.72rem;
      opacity: 0.9;
    }

    #axs-chat-close {
      margin-left: auto;
      width: 30px;
      height: 30px;
      border: 0;
      border-radius: 50%;
      background: transparent;
      color: #fff;
      font-size: 1.35rem;
      line-height: 1;
      cursor: pointer;
      opacity: 0.9;
    }

    #axs-chat-close:hover {
      background: rgba(255,255,255,0.12);
      opacity: 1;
    }

    #axs-chat-messages {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      color: #111827;
    }

    .axs-chat-message {
      max-width: 86%;
      padding: 11px 13px;
      border-radius: 10px;
      white-space: pre-wrap;
      line-height: 1.55;
      font-size: 0.88rem;
      overflow-wrap: anywhere;
    }

    .axs-chat-message.assistant {
      align-self: flex-start;
      background: #fff;
      color: #111827;
      box-shadow: 0 2px 10px rgba(12,30,54,0.08);
    }

    .axs-chat-message.user {
      align-self: flex-end;
      background: #13598f;
      color: #fff;
      border-bottom-right-radius: 4px;
    }

    .axs-chat-message.typing {
      color: #64748b;
      font-style: italic;
    }

    #axs-chat-form {
      flex: 0 0 auto;
      display: grid;
      grid-template-columns: 1fr 42px;
      gap: 8px;
      padding: 10px;
      background: #fff;
      border-top: 1px solid #dce5ef;
    }

    #axs-chat-input {
      min-height: 38px;
      max-height: 100px;
      resize: none;
      border: 1px solid #cbd7e4;
      border-radius: 8px;
      padding: 10px 11px;
      font: inherit;
      color: #0f172a;
      outline: none;
    }

    #axs-chat-input:focus {
      border-color: #13598f;
      box-shadow: 0 0 0 3px rgba(19,89,143,0.11);
    }

    #axs-chat-send {
      border: 0;
      border-radius: 8px;
      background: #13598f;
      color: #fff;
      display: grid;
      place-items: center;
      cursor: pointer;
    }

    #axs-chat-send:disabled {
      opacity: 0.55;
      cursor: wait;
    }

    #axs-chat-send svg {
      width: 22px;
      height: 22px;
    }

    @media (max-width: 520px) {
      #axs-chat-box {
        right: 10px !important;
        bottom: 82px !important;
        width: calc(100vw - 20px) !important;
        height: min(620px, calc(100vh - 94px));
      }

      #axs-chat-btn {
        right: 14px;
        bottom: 14px;
      }
    }
  `;
  document.head.appendChild(style);

  document.body.insertAdjacentHTML("beforeend", `
    <button id="axs-chat-btn" type="button" title="Assistente AXS" aria-label="Abrir Assistente AXS">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M5 5.5h14a1.5 1.5 0 0 1 1.5 1.5v8.2a1.5 1.5 0 0 1-1.5 1.5H9.2L4.5 20v-3.3H5A1.5 1.5 0 0 1 3.5 15.2V7A1.5 1.5 0 0 1 5 5.5Z"/>
      </svg>
    </button>

    <section id="axs-chat-box" aria-label="Assistente AXS">
      <header id="axs-chat-header">
        <img src="./logo.png" alt="AXS Energia">
        <div id="axs-chat-title">
          <strong>Assistente AXS</strong>
          <small>Perguntas sobre os contratos e emissoes</small>
        </div>
        <button id="axs-chat-close" type="button" aria-label="Fechar">x</button>
      </header>
      <div id="axs-chat-messages"></div>
      <form id="axs-chat-form">
        <textarea id="axs-chat-input" rows="1" placeholder="Digite sua pergunta..."></textarea>
        <button id="axs-chat-send" type="submit" title="Enviar">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M4.2 4.7 20.4 12 4.2 19.3l.9-6.1L13.8 12 5.1 10.8l-.9-6.1Z"/>
          </svg>
        </button>
      </form>
    </section>
  `);

  const button = document.getElementById("axs-chat-btn");
  const box = document.getElementById("axs-chat-box");
  const close = document.getElementById("axs-chat-close");
  const header = document.getElementById("axs-chat-header");
  const messages = document.getElementById("axs-chat-messages");
  const form = document.getElementById("axs-chat-form");
  const input = document.getElementById("axs-chat-input");
  const send = document.getElementById("axs-chat-send");

  function addMessage(text, type) {
    const node = document.createElement("div");
    node.className = `axs-chat-message ${type}`;
    node.textContent = text;
    messages.appendChild(node);
    messages.scrollTop = messages.scrollHeight;
    return node;
  }

  function setOpen(open) {
    box.classList.toggle("open", open);
    if (open) input.focus();
  }

  button.addEventListener("click", () => setOpen(!box.classList.contains("open")));
  close.addEventListener("click", () => setOpen(false));

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 100)}px`;
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startRight = 0;
  let startBottom = 0;

  header.addEventListener("mousedown", (event) => {
    if (event.target === close) return;
    const rect = box.getBoundingClientRect();
    dragging = true;
    startX = event.clientX;
    startY = event.clientY;
    startRight = window.innerWidth - rect.right;
    startBottom = window.innerHeight - rect.bottom;
    document.body.style.userSelect = "none";
  });

  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    box.style.right = `${Math.max(8, startRight + startX - event.clientX)}px`;
    box.style.bottom = `${Math.max(8, startBottom + startY - event.clientY)}px`;
  });

  document.addEventListener("mouseup", () => {
    dragging = false;
    document.body.style.userSelect = "";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || loading) return;

    loading = true;
    send.disabled = true;
    input.value = "";
    input.style.height = "auto";
    addMessage(question, "user");
    const typing = addMessage("Analisando documentos e calculos...", "assistant typing");

    history.push({ role: "user", content: question });
    if (history.length > MAX_HISTORY) history = history.slice(-MAX_HISTORY);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pergunta: question, historico: history.slice(0, -1) }),
      });
      const data = await response.json();
      typing.remove();
      if (!response.ok) throw new Error(data.erro || data.error || `Erro ${response.status}`);
      const answer = data.resposta || "Nao consegui montar uma resposta agora.";
      addMessage(answer, "assistant");
      history.push({ role: "assistant", content: answer });
    } catch (error) {
      typing.remove();
      addMessage(`Nao consegui consultar a IA agora. Detalhe: ${error.message}`, "assistant");
      history.pop();
    } finally {
      loading = false;
      send.disabled = false;
      input.focus();
    }
  });

  addMessage(INITIAL_MESSAGE, "assistant");
})();
