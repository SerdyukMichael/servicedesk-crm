import { useState } from "react";

const STATUSES = [
  { code: "S1", label: "Новая", color: "#3b82f6", en: "New" },
  { code: "S2", label: "Назначена", color: "#8b5cf6", en: "Assigned" },
  { code: "S3", label: "В работе", color: "#f59e0b", en: "In Progress" },
  { code: "S4", label: "Ожидание запчасти", color: "#ef4444", en: "Waiting" },
  { code: "S5", label: "Выполнена", color: "#10b981", en: "Completed" },
  { code: "S6", label: "На проверке", color: "#6366f1", en: "Review" },
  { code: "S7", label: "Закрыта", color: "#6b7280", en: "Closed" },
];

const PRIORITIES = [
  { value: "critical", label: "Критичный", color: "#dc2626" },
  { value: "high", label: "Высокий", color: "#f97316" },
  { value: "medium", label: "Средний", color: "#eab308" },
  { value: "low", label: "Низкий", color: "#22c55e" },
];

const WORK_TYPES = ["Гарантийный ремонт", "Плановое ТО", "Внеплановый ремонт", "Установка"];

const MOCK_DATA = [
  { id: "SR/2026/03/001", client: "PKO Bank Polski", equipment: "Matica S7000 (SN: MT-2024-00142)", status: "S1", priority: "critical", type: "Внеплановый ремонт", created: "2026-03-15 09:30", engineer: null, slaResp: "11:30", slaResol: "2026-03-16 09:30", desc: "Банкомат не выдает купюры, ошибка E-4012 на дисплее" },
  { id: "SR/2026/03/002", client: "mBank S.A.", equipment: "Matica C310 (SN: MC-2023-00087)", status: "S3", priority: "high", type: "Гарантийный ремонт", created: "2026-03-14 14:20", engineer: "Ковальски Я.", slaResp: "16:20", slaResol: "2026-03-15 14:20", desc: "Карт-машина зажевывает пластик при персонализации" },
  { id: "SR/2026/03/003", client: "ING Bank Slaski", equipment: "Matica S5000 (SN: MT-2023-00215)", status: "S5", priority: "medium", type: "Плановое ТО", created: "2026-03-13 08:00", engineer: "Новак А.", slaResp: "16:00", slaResol: "2026-03-16 08:00", desc: "Ежеквартальное ТО" },
  { id: "SR/2026/03/004", client: "Santander Bank Polska", equipment: "Matica S7000 (SN: MT-2025-00301)", status: "S4", priority: "high", type: "Внеплановый ремонт", created: "2026-03-12 11:45", engineer: "Ковальски Я.", slaResp: "13:45", slaResol: "2026-03-15 11:45", desc: "Сбой считывателя карт, требуется замена модуля CR-500" },
  { id: "SR/2026/03/005", client: "BNP Paribas", equipment: "Matica C310 (SN: MC-2024-00156)", status: "S7", priority: "low", type: "Установка", created: "2026-03-10 10:00", engineer: "Вишневски П.", slaResp: "18:00", slaResol: "2026-03-13 10:00", desc: "Установка и настройка новой карт-машины" },
];

const Badge = ({ color, children }) => (
  <span style={{ background: color + "18", color, padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", border: `1px solid ${color}30` }}>{children}</span>
);

const Field = ({ label, required, children, hint, readonly, hidden }) => {
  if (hidden) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#475569", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label} {required && <span style={{ color: "#ef4444" }}>*</span>}
        {readonly && <span style={{ color: "#94a3b8", fontWeight: 400, textTransform: "none" }}> (только чтение)</span>}
      </label>
      {children}
      {hint && <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{hint}</div>}
    </div>
  );
};

const Input = ({ placeholder, value, readonly, type = "text", ...props }) => (
  <input
    type={type}
    placeholder={placeholder}
    defaultValue={value}
    readOnly={readonly}
    style={{
      width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 6,
      fontSize: 14, background: readonly ? "#f8fafc" : "#fff", color: "#1e293b",
      outline: "none", boxSizing: "border-box",
      cursor: readonly ? "not-allowed" : "text"
    }}
    {...props}
  />
);

const Select = ({ options, value, readonly, placeholder }) => (
  <select
    defaultValue={value || ""}
    disabled={readonly}
    style={{
      width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 6,
      fontSize: 14, background: readonly ? "#f8fafc" : "#fff", color: "#1e293b",
      cursor: readonly ? "not-allowed" : "pointer"
    }}
  >
    {placeholder && <option value="">{placeholder}</option>}
    {options.map(o => <option key={o.value || o} value={o.value || o}>{o.label || o}</option>)}
  </select>
);

const Textarea = ({ placeholder, value, readonly, rows = 4 }) => (
  <textarea
    placeholder={placeholder}
    defaultValue={value}
    readOnly={readonly}
    rows={rows}
    style={{
      width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 6,
      fontSize: 14, background: readonly ? "#f8fafc" : "#fff", color: "#1e293b",
      resize: "vertical", fontFamily: "inherit", boxSizing: "border-box"
    }}
  />
);

const Btn = ({ children, variant = "default", onClick, size = "md" }) => {
  const styles = {
    primary: { background: "#2563eb", color: "#fff", border: "none" },
    success: { background: "#16a34a", color: "#fff", border: "none" },
    danger: { background: "#dc2626", color: "#fff", border: "none" },
    warning: { background: "#f59e0b", color: "#fff", border: "none" },
    default: { background: "#fff", color: "#334155", border: "1px solid #e2e8f0" },
    ghost: { background: "transparent", color: "#64748b", border: "none" },
  };
  const sizes = {
    sm: { padding: "4px 10px", fontSize: 12 },
    md: { padding: "8px 16px", fontSize: 13 },
    lg: { padding: "10px 24px", fontSize: 14 },
  };
  return (
    <button onClick={onClick} style={{ ...styles[variant], ...sizes[size], borderRadius: 6, fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
      {children}
    </button>
  );
};

const Card = ({ children, style }) => (
  <div style={{ background: "#fff", borderRadius: 10, border: "1px solid #e2e8f0", padding: 20, ...style }}>{children}</div>
);

const StatusTimeline = ({ current }) => {
  const idx = STATUSES.findIndex(s => s.code === current);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 20, overflowX: "auto", paddingBottom: 4 }}>
      {STATUSES.map((s, i) => (
        <div key={s.code} style={{ display: "flex", alignItems: "center" }}>
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: i <= idx ? s.color : "#e2e8f0",
            color: i <= idx ? "#fff" : "#94a3b8",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, fontWeight: 700, flexShrink: 0
          }}>{i + 1}</div>
          <div style={{ fontSize: 10, color: i === idx ? s.color : "#94a3b8", fontWeight: i === idx ? 700 : 400, marginLeft: 4, marginRight: 8, whiteSpace: "nowrap" }}>{s.label}</div>
          {i < STATUSES.length - 1 && <div style={{ width: 20, height: 2, background: i < idx ? STATUSES[i + 1].color : "#e2e8f0", flexShrink: 0 }} />}
        </div>
      ))}
    </div>
  );
};

// ==================== SCREEN 1: LIST ====================
const ListScreen = ({ onView, onCreate }) => {
  const [filters, setFilters] = useState({ status: "", priority: "", engineer: "", search: "" });
  const [showFilters, setShowFilters] = useState(false);
  const filtered = MOCK_DATA.filter(r => {
    if (filters.status && r.status !== filters.status) return false;
    if (filters.priority && r.priority !== filters.priority) return false;
    if (filters.search && !r.id.toLowerCase().includes(filters.search.toLowerCase()) && !r.client.toLowerCase().includes(filters.search.toLowerCase()) && !r.equipment.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, color: "#0f172a" }}>Заявки на обслуживание</h2>
          <div style={{ fontSize: 13, color: "#64748b" }}>Service Requests | Найдено: {filtered.length}</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="ghost" onClick={() => setShowFilters(!showFilters)}>
            {showFilters ? "Скрыть фильтры" : "Фильтры"}
          </Btn>
          <Btn variant="primary" onClick={onCreate}>+ Новая заявка</Btn>
        </div>
      </div>

      {showFilters && (
        <Card style={{ marginBottom: 16, background: "#f8fafc" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
            <Field label="Поиск">
              <Input placeholder="Номер, клиент, оборудование..." value={filters.search} onChange={e => setFilters(f => ({ ...f, search: e.target.value }))} />
            </Field>
            <Field label="Статус">
              <Select options={[{ value: "", label: "Все статусы" }, ...STATUSES.map(s => ({ value: s.code, label: s.label }))]} value={filters.status} />
            </Field>
            <Field label="Приоритет">
              <Select options={[{ value: "", label: "Все" }, ...PRIORITIES.map(p => ({ value: p.value, label: p.label }))]} value={filters.priority} />
            </Field>
            <Field label="Инженер">
              <Select options={[{ value: "", label: "Все" }, "Ковальски Я.", "Новак А.", "Вишневски П."].map(e => typeof e === "string" ? { value: e, label: e } : e)} />
            </Field>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <Btn variant="primary" size="sm">Применить</Btn>
            <Btn size="sm" onClick={() => setFilters({ status: "", priority: "", engineer: "", search: "" })}>Сбросить</Btn>
          </div>
        </Card>
      )}

      <Card style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f8fafc" }}>
                {["Номер", "Клиент", "Оборудование", "Тип", "Приоритет", "Статус", "Инженер", "Создана", "SLA решение"].map(h => (
                  <th key={h} style={{ padding: "10px 12px", textAlign: "left", color: "#64748b", fontWeight: 600, fontSize: 11, textTransform: "uppercase", borderBottom: "1px solid #e2e8f0", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => {
                const st = STATUSES.find(s => s.code === r.status);
                const pr = PRIORITIES.find(p => p.value === r.priority);
                return (
                  <tr key={r.id} onClick={() => onView(r)} style={{ cursor: "pointer", borderBottom: "1px solid #f1f5f9" }}
                    onMouseEnter={e => e.currentTarget.style.background = "#f8fafc"}
                    onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <td style={{ padding: "10px 12px", fontWeight: 600, color: "#2563eb", whiteSpace: "nowrap" }}>{r.id}</td>
                    <td style={{ padding: "10px 12px" }}>{r.client}</td>
                    <td style={{ padding: "10px 12px", fontSize: 12, color: "#64748b" }}>{r.equipment}</td>
                    <td style={{ padding: "10px 12px", fontSize: 12 }}>{r.type}</td>
                    <td style={{ padding: "10px 12px" }}><Badge color={pr.color}>{pr.label}</Badge></td>
                    <td style={{ padding: "10px 12px" }}><Badge color={st.color}>{st.label}</Badge></td>
                    <td style={{ padding: "10px 12px" }}>{r.engineer || <span style={{ color: "#cbd5e1" }}>---</span>}</td>
                    <td style={{ padding: "10px 12px", fontSize: 12, color: "#64748b", whiteSpace: "nowrap" }}>{r.created}</td>
                    <td style={{ padding: "10px 12px", fontSize: 12, whiteSpace: "nowrap" }}>{r.slaResol}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div style={{ padding: "10px 12px", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, color: "#64748b" }}>
          <span>Показано {filtered.length} из {MOCK_DATA.length}</span>
          <div style={{ display: "flex", gap: 4 }}>
            <Btn size="sm" variant="ghost">Prev</Btn>
            <Btn size="sm" variant="primary">1</Btn>
            <Btn size="sm" variant="ghost">2</Btn>
            <Btn size="sm" variant="ghost">Next</Btn>
          </div>
        </div>
      </Card>
    </div>
  );
};

// ==================== SCREEN 2: CREATE ====================
const CreateScreen = ({ onBack }) => (
  <div>
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
      <Btn variant="ghost" onClick={onBack}>← Назад</Btn>
      <div>
        <h2 style={{ margin: 0, fontSize: 20, color: "#0f172a" }}>Новая заявка на обслуживание</h2>
        <div style={{ fontSize: 13, color: "#64748b" }}>Create Service Request | Статус: Новая</div>
      </div>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
      <Card>
        <h3 style={{ margin: "0 0 16px", fontSize: 15, color: "#0f172a", borderBottom: "1px solid #f1f5f9", paddingBottom: 8 }}>Основная информация</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Field label="Клиент" required hint="Выберите клиента из справочника">
            <Select options={["PKO Bank Polski", "mBank S.A.", "ING Bank Slaski", "Santander Bank Polska", "BNP Paribas"].map(c => ({ value: c, label: c }))} placeholder="-- Выберите клиента --" />
          </Field>
          <Field label="Контактное лицо" hint="Автоматически из контактов клиента">
            <Select options={[]} placeholder="Сначала выберите клиента" />
          </Field>
          <Field label="Оборудование" required hint="Серийный номер устройства клиента">
            <Select options={[]} placeholder="Сначала выберите клиента" />
          </Field>
          <Field label="Тип работ" required hint="Вид обслуживания">
            <Select options={WORK_TYPES.map(t => ({ value: t, label: t }))} placeholder="-- Выберите тип --" />
          </Field>
          <Field label="Приоритет" required hint="Авторасчет из договора + тип оборудования">
            <Select options={PRIORITIES.map(p => p)} placeholder="Автоматически" />
          </Field>
          <Field label="Договор обслуживания" hint="Определяется автоматически">
            <Input value="SA/2026/012 (Премиум)" readonly />
          </Field>
        </div>
        <Field label="Описание проблемы" required hint="Минимум 10 символов">
          <Textarea placeholder="Подробно опишите проблему..." />
        </Field>
        <Field label="Вложения" hint="PDF, JPEG, PNG, DOCX. Макс. 20 МБ, до 50 файлов">
          <div style={{ border: "2px dashed #e2e8f0", borderRadius: 8, padding: 20, textAlign: "center", color: "#94a3b8", cursor: "pointer" }}>
            Перетащите файлы сюда или нажмите для выбора
          </div>
        </Field>
      </Card>
      <div>
        <Card style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 15, color: "#0f172a" }}>SLA (автоматически)</h3>
          <Field label="Время реакции" hint="Из договора обслуживания">
            <Input value="2 часа (Премиум)" readonly />
          </Field>
          <Field label="Дедлайн реакции">
            <Input value="Расчет после сохранения" readonly />
          </Field>
          <Field label="Время решения" hint="Из договора обслуживания">
            <Input value="24 часа (Премиум)" readonly />
          </Field>
          <Field label="Дедлайн решения">
            <Input value="Расчет после сохранения" readonly />
          </Field>
        </Card>
        <Card style={{ background: "#fffbeb", borderColor: "#fde68a" }}>
          <div style={{ fontSize: 13, color: "#92400e", fontWeight: 600, marginBottom: 6 }}>Проверки при сохранении:</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#92400e", lineHeight: 1.8 }}>
            <li>Клиент выбран</li>
            <li>Оборудование выбрано</li>
            <li>Тип работ указан</li>
            <li>Описание >= 10 символов</li>
          </ul>
        </Card>
      </div>
    </div>
    <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
      <Btn onClick={onBack}>Отмена</Btn>
      <Btn variant="primary">Сохранить (статус: Новая)</Btn>
    </div>
  </div>
);

// ==================== SCREEN 3: VIEW/EDIT ====================
const ViewScreen = ({ record, onBack, onChangeStatus, currentStatus, setCurrentStatus }) => {
  const st = STATUSES.find(s => s.code === currentStatus);
  const isNew = currentStatus === "S1";
  const isAssigned = currentStatus === "S2";
  const isInProgress = currentStatus === "S3";
  const isWaiting = currentStatus === "S4";
  const isCompleted = currentStatus === "S5";
  const isReview = currentStatus === "S6";
  const isClosed = currentStatus === "S7";

  const showWorkFields = isInProgress || isWaiting || isCompleted || isReview || isClosed;
  const editWorkFields = isInProgress || isCompleted;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Btn variant="ghost" onClick={onBack}>← Назад</Btn>
          <div>
            <h2 style={{ margin: 0, fontSize: 20, color: "#0f172a" }}>{record.id}</h2>
            <div style={{ fontSize: 13, color: "#64748b" }}>Service Request | {record.client}</div>
          </div>
          <Badge color={st.color}>{st.label}</Badge>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {isNew && <Btn variant="primary" onClick={() => setCurrentStatus("S2")}>Назначить инженера</Btn>}
          {isAssigned && <Btn variant="warning" onClick={() => setCurrentStatus("S3")}>Начать работу</Btn>}
          {isInProgress && <Btn variant="danger" onClick={() => setCurrentStatus("S4")}>Ожидание запчасти</Btn>}
          {isInProgress && <Btn variant="success" onClick={() => setCurrentStatus("S5")}>Работа выполнена</Btn>}
          {isWaiting && <Btn variant="warning" onClick={() => setCurrentStatus("S3")}>Продолжить работу</Btn>}
          {isReview && <Btn variant="success" onClick={() => setCurrentStatus("S7")}>Принять и закрыть</Btn>}
          {isReview && <Btn variant="danger" onClick={() => setCurrentStatus("S3")}>Вернуть на доработку</Btn>}
          <Btn variant="ghost">Печать PDF</Btn>
        </div>
      </div>

      <StatusTimeline current={currentStatus} />

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
        <div>
          <Card style={{ marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 16px", fontSize: 15, color: "#0f172a", borderBottom: "1px solid #f1f5f9", paddingBottom: 8 }}>Информация о заявке</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Field label="Клиент" readonly={!isNew}>
                <Input value={record.client} readonly />
              </Field>
              <Field label="Оборудование" readonly={!isNew}>
                <Input value={record.equipment} readonly />
              </Field>
              <Field label="Тип работ" readonly>
                <Input value={record.type} readonly />
              </Field>
              <Field label="Приоритет" readonly={!isNew && !isAssigned}>
                <Select options={PRIORITIES} value={record.priority} readonly={!isNew && !isAssigned} />
              </Field>
            </div>
            <Field label="Описание проблемы" readonly={!isNew && !isAssigned}>
              <Textarea value={record.desc} readonly={!isNew && !isAssigned} />
            </Field>
          </Card>

          {isNew && (
            <Card style={{ marginBottom: 16, borderColor: "#3b82f6", borderWidth: 2 }}>
              <h3 style={{ margin: "0 0 16px", fontSize: 15, color: "#2563eb" }}>Назначение инженера</h3>
              <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 12px" }}>Выберите инженера, сертифицированного на модель оборудования. Отсортировано по загрузке.</p>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#eff6ff" }}>
                    <th style={{ padding: 8, textAlign: "left", fontSize: 11 }}>Инженер</th>
                    <th style={{ padding: 8, textAlign: "center", fontSize: 11 }}>Сертификат</th>
                    <th style={{ padding: 8, textAlign: "center", fontSize: 11 }}>Открытых заявок</th>
                    <th style={{ padding: 8, textAlign: "center", fontSize: 11 }}>Статус</th>
                    <th style={{ padding: 8, fontSize: 11 }}></th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: 8 }}>Новак А.</td>
                    <td style={{ padding: 8, textAlign: "center" }}><Badge color="#16a34a">S7000</Badge></td>
                    <td style={{ padding: 8, textAlign: "center" }}>2</td>
                    <td style={{ padding: 8, textAlign: "center" }}><Badge color="#22c55e">Доступен</Badge></td>
                    <td style={{ padding: 8 }}><Btn variant="primary" size="sm">Назначить</Btn></td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: 8 }}>Ковальски Я.</td>
                    <td style={{ padding: 8, textAlign: "center" }}><Badge color="#16a34a">S7000, S5000</Badge></td>
                    <td style={{ padding: 8, textAlign: "center" }}>4</td>
                    <td style={{ padding: 8, textAlign: "center" }}><Badge color="#f59e0b">Занят</Badge></td>
                    <td style={{ padding: 8 }}><Btn size="sm">Назначить</Btn></td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid #f1f5f9", opacity: 0.5 }}>
                    <td style={{ padding: 8 }}>Вишневски П.</td>
                    <td style={{ padding: 8, textAlign: "center" }}><Badge color="#94a3b8">C310</Badge></td>
                    <td style={{ padding: 8, textAlign: "center" }}>1</td>
                    <td style={{ padding: 8, textAlign: "center" }}><Badge color="#ef4444">Не серт.</Badge></td>
                    <td style={{ padding: 8, fontSize: 11, color: "#ef4444" }}>Не сертифицирован на S7000</td>
                  </tr>
                </tbody>
              </table>
            </Card>
          )}

          {showWorkFields && (
            <Card style={{ marginBottom: 16 }}>
              <h3 style={{ margin: "0 0 16px", fontSize: 15, color: "#0f172a", borderBottom: "1px solid #f1f5f9", paddingBottom: 8 }}>Акт выполненных работ</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                <Field label="Время в пути (мин)" readonly={!editWorkFields}>
                  <Input type="number" placeholder="0" value={isCompleted || isReview || isClosed ? "45" : ""} readonly={!editWorkFields} />
                </Field>
                <Field label="Время работы (мин)" required readonly={!editWorkFields} hint="Обязательно > 0">
                  <Input type="number" placeholder="0" value={isCompleted || isReview || isClosed ? "180" : ""} readonly={!editWorkFields} />
                </Field>
                <Field label="Инженер" readonly>
                  <Input value={record.engineer || "Не назначен"} readonly />
                </Field>
              </div>
              <Field label="Описание выполненных работ" required readonly={!editWorkFields} hint="Минимум 20 символов">
                <Textarea
                  placeholder="Подробно опишите что было сделано..."
                  value={isCompleted || isReview || isClosed ? "Проведена диагностика модуля выдачи купюр. Обнаружен износ роликов подачи. Произведена замена роликов (2 шт). Проведена калибровка и тестирование. Банкомат работает штатно." : ""}
                  readonly={!editWorkFields}
                />
              </Field>

              <h4 style={{ margin: "16px 0 8px", fontSize: 13, color: "#475569" }}>Использованные запчасти</h4>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, marginBottom: 12 }}>
                <thead>
                  <tr style={{ background: "#f8fafc" }}>
                    <th style={{ padding: 8, textAlign: "left", fontSize: 11 }}>Запчасть</th>
                    <th style={{ padding: 8, textAlign: "center", fontSize: 11 }}>Кол-во</th>
                    <th style={{ padding: 8, textAlign: "center", fontSize: 11 }}>Склад</th>
                    {editWorkFields && <th style={{ padding: 8, fontSize: 11 }}></th>}
                  </tr>
                </thead>
                <tbody>
                  {(isCompleted || isReview || isClosed) && (
                    <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: 8 }}>Ролик подачи купюр RP-200</td>
                      <td style={{ padding: 8, textAlign: "center" }}>2</td>
                      <td style={{ padding: 8, textAlign: "center" }}>Основной</td>
                      {editWorkFields && <td style={{ padding: 8 }}><Btn variant="danger" size="sm">x</Btn></td>}
                    </tr>
                  )}
                </tbody>
              </table>
              {editWorkFields && <Btn size="sm">+ Добавить запчасть</Btn>}

              <h4 style={{ margin: "16px 0 8px", fontSize: 13, color: "#475569" }}>Фото до/после</h4>
              {editWorkFields ? (
                <div style={{ border: "2px dashed #e2e8f0", borderRadius: 8, padding: 16, textAlign: "center", color: "#94a3b8", fontSize: 12 }}>
                  Минимум 1 фото. JPEG/PNG, до 10 МБ. Перетащите или нажмите.
                </div>
              ) : (
                <div style={{ display: "flex", gap: 8 }}>
                  {[1, 2].map(i => (
                    <div key={i} style={{ width: 80, height: 80, background: "#f1f5f9", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, color: "#cbd5e1" }}>img</div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {isInProgress && (
            <Card style={{ borderColor: "#ef4444", background: "#fef2f2" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 15, color: "#dc2626" }}>Ожидание запчасти</h3>
              <Field label="Ожидаемая запчасть" required hint="Укажите какую запчасть ожидаете">
                <Select options={["Модуль CR-500", "Ролик подачи RP-200", "Плата управления MB-100"].map(p => ({ value: p, label: p }))} placeholder="-- Выберите --" />
              </Field>
              <Field label="Причина ожидания">
                <Textarea placeholder="Опишите причину..." rows={2} />
              </Field>
            </Card>
          )}

          <Card style={{ marginTop: 16 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, color: "#0f172a" }}>Комментарии</h3>
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <Btn size="sm" variant="primary">Внутренний</Btn>
              <Btn size="sm">Внешний (виден клиенту)</Btn>
            </div>
            <div style={{ background: "#f8fafc", borderRadius: 8, padding: 12, marginBottom: 8, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>Ковальски Я.</span>
                <span style={{ color: "#94a3b8", fontSize: 11 }}>2026-03-15 10:15 <Badge color="#8b5cf6">внутренний</Badge></span>
              </div>
              Требуется замена модуля CR-500, заказал у поставщика. Ожидание 2-3 дня.
            </div>
            <Textarea placeholder="Добавить комментарий..." rows={2} />
            <div style={{ marginTop: 8, textAlign: "right" }}><Btn variant="primary" size="sm">Отправить</Btn></div>
          </Card>
        </div>

        <div>
          <Card style={{ marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, color: "#0f172a" }}>SLA</h3>
            <div style={{ display: "grid", gap: 8, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#64748b" }}>Реакция:</span>
                <span style={{ fontWeight: 600 }}>2 ч (Премиум)</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#64748b" }}>Дедлайн реакции:</span>
                <span style={{ fontWeight: 600 }}>{record.slaResp}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#64748b" }}>SLA реакция:</span>
                <Badge color={record.engineer ? "#16a34a" : "#ef4444"}>{record.engineer ? "Соблюден" : "В процессе"}</Badge>
              </div>
              <hr style={{ border: "none", borderTop: "1px solid #f1f5f9" }} />
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#64748b" }}>Решение:</span>
                <span style={{ fontWeight: 600 }}>24 ч</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#64748b" }}>Дедлайн решения:</span>
                <span style={{ fontWeight: 600 }}>{record.slaResol}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#64748b" }}>SLA решение:</span>
                <Badge color={isClosed ? "#16a34a" : "#f59e0b"}>{isClosed ? "Соблюден" : "В процессе"}</Badge>
              </div>
            </div>
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, color: "#0f172a" }}>Детали</h3>
            <div style={{ fontSize: 13, display: "grid", gap: 6 }}>
              <div><span style={{ color: "#64748b" }}>Создана:</span> {record.created}</div>
              <div><span style={{ color: "#64748b" }}>Инженер:</span> {record.engineer || "---"}</div>
              <div><span style={{ color: "#64748b" }}>Договор:</span> SA/2026/012</div>
              <div><span style={{ color: "#64748b" }}>Тип:</span> {record.type}</div>
            </div>
          </Card>

          <Card style={{ background: "#f0fdf4", borderColor: "#bbf7d0" }}>
            <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#166534" }}>Оборудование</h3>
            <div style={{ fontSize: 12, color: "#166534", display: "grid", gap: 4 }}>
              <div><b>Модель:</b> Matica S7000</div>
              <div><b>S/N:</b> MT-2024-00142</div>
              <div><b>Гарантия:</b> <Badge color="#16a34a">Активна до 12.2026</Badge></div>
              <div><b>Ремонтов:</b> 2</div>
              <div><b>Посл. ТО:</b> 2025-12-15</div>
            </div>
          </Card>

          {(isReview || isClosed) && (
            <Card style={{ marginTop: 16, background: "#eff6ff", borderColor: "#93c5fd" }}>
              <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#1e40af" }}>Проверки закрытия</h3>
              <div style={{ fontSize: 12, color: "#1e40af" }}>
                {["Акт сохранен", "Описание работ >= 20 символов", "Время работы > 0", "Минимум 1 фото"].map(c => (
                  <div key={c} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <span style={{ color: "#16a34a", fontWeight: 700 }}>OK</span> {c}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== MAIN APP ====================
export default function App() {
  const [screen, setScreen] = useState("list");
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [currentStatus, setCurrentStatus] = useState("S1");
  const [role, setRole] = useState("manager");

  const ROLES = [
    { value: "manager", label: "Рук. сервиса" },
    { value: "engineer", label: "Инженер" },
    { value: "director", label: "Директор" },
    { value: "sales", label: "Менеджер по продажам" },
  ];

  return (
    <div style={{ fontFamily: "'Segoe UI', -apple-system, sans-serif", background: "#f1f5f9", minHeight: "100vh" }}>
      <header style={{ background: "#0f172a", color: "#fff", padding: "10px 20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontWeight: 700, fontSize: 16 }}>ServiceDesk CRM</span>
          <nav style={{ display: "flex", gap: 4 }}>
            {["Клиенты", "Сделки", "Заявки", "Оборудование", "Склад", "Счета", "Вендоры"].map(item => (
              <span key={item} style={{ padding: "4px 10px", borderRadius: 4, fontSize: 13, cursor: "pointer", background: item === "Заявки" ? "#2563eb" : "transparent", color: item === "Заявки" ? "#fff" : "#94a3b8" }}>{item}</span>
            ))}
          </nav>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <select
            value={role}
            onChange={e => setRole(e.target.value)}
            style={{ background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "4px 8px", fontSize: 12 }}
          >
            {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#2563eb", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>
            {role === "manager" ? "RS" : role === "engineer" ? "SI" : role === "director" ? "D" : "MP"}
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1200, margin: "0 auto", padding: 20 }}>
        {screen === "list" && (
          <ListScreen
            onView={(r) => { setSelectedRecord(r); setCurrentStatus(r.status); setScreen("view"); }}
            onCreate={() => setScreen("create")}
          />
        )}
        {screen === "create" && <CreateScreen onBack={() => setScreen("list")} />}
        {screen === "view" && selectedRecord && (
          <ViewScreen
            record={selectedRecord}
            onBack={() => setScreen("list")}
            currentStatus={currentStatus}
            setCurrentStatus={setCurrentStatus}
          />
        )}
      </main>

      <footer style={{ textAlign: "center", padding: 12, fontSize: 11, color: "#94a3b8" }}>
        ServiceDesk CRM Wireframes | Д-09: Заявка на обслуживание | v1.0
      </footer>
    </div>
  );
}
