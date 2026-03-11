import type { ReactNode } from "react";

interface SettingsSectionProps {
  title: string;
  description?: string;
  children: ReactNode;
}

export function SettingsSection({ title, description, children }: SettingsSectionProps) {
  return (
    <section className="settings-group">
      <header>
        <h3>{title}</h3>
        {description ? <p className="status-muted">{description}</p> : null}
      </header>
      {children}
    </section>
  );
}

interface SettingsFieldProps {
  label: string;
  description?: string;
  children: ReactNode;
}

export function SettingsField({ label, description, children }: SettingsFieldProps) {
  return (
    <div className="settings-field">
      <div className="settings-field-head">
        <strong>{label}</strong>
        {description ? <p className="status-muted">{description}</p> : null}
      </div>
      <div className="settings-field-control">{children}</div>
    </div>
  );
}

interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

interface SettingsSegmentedProps<T extends string> {
  value: T;
  options: Array<SegmentedOption<T>>;
  on_change: (value: T) => void;
}

export function SettingsSegmented<T extends string>({ value, options, on_change }: SettingsSegmentedProps<T>) {
  return (
    <div className="settings-segmented" role="group" aria-label="Segmentierte Auswahl">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={option.value === value ? "settings-segmented-option is-active" : "settings-segmented-option"}
          onClick={() => {
            on_change(option.value);
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

interface SettingsToggleProps {
  checked: boolean;
  on_change: (next: boolean) => void;
}

export function SettingsToggle({ checked, on_change }: SettingsToggleProps) {
  return (
    <label className="settings-toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => {
          on_change(event.target.checked);
        }}
      />
      <span>{checked ? "Aktiv" : "Inaktiv"}</span>
    </label>
  );
}

interface SelectOption<T extends string> {
  value: T;
  label: string;
}

interface SettingsSelectProps<T extends string> {
  value: T;
  options: Array<SelectOption<T>>;
  on_change: (value: T) => void;
}

export function SettingsSelect<T extends string>({ value, options, on_change }: SettingsSelectProps<T>) {
  return (
    <select
      className="settings-select"
      value={value}
      onChange={(event) => {
        on_change(event.target.value as T);
      }}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

interface SettingsRangeProps {
  value: number;
  min: number;
  max: number;
  step?: number;
  on_change: (value: number) => void;
}

export function SettingsRange({ value, min, max, step = 1, on_change }: SettingsRangeProps) {
  return (
    <div className="settings-range">
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => {
          on_change(Number(event.target.value));
        }}
      />
      <span>{value}</span>
    </div>
  );
}
