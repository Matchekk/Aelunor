import { SettingsDialog } from "./SettingsDialog";

interface DisplaySettingsDialogProps {
  open: boolean;
  on_close: () => void;
  return_focus_element?: HTMLElement | null;
}

export function DisplaySettingsDialog({ open, on_close, return_focus_element = null }: DisplaySettingsDialogProps) {
  return <SettingsDialog open={open} on_close={on_close} return_focus_element={return_focus_element} />;
}
