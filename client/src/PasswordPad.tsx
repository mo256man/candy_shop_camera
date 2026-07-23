import { useState } from "react";
import "./PasswordPad.css";

const PASSWORD = "0000"; // 4桁のパスワード
const MAX_LENGTH = 4;

const KEYS = ["7", "8", "9", "4", "5", "6", "1", "2", "3", "C", "0", "E"] as const;

type PasswordPadProps = {
  isAdmin: boolean;
  onAdminChange: (isAdmin: boolean) => void;
};

export default function PasswordPad({ isAdmin, onAdminChange }: PasswordPadProps) {
  const [input, setInput] = useState<string>("");

  const handleKey = (key: string): void => {
    if (key === "C") {
      setInput("");
      return;
    }
    if (key === "E") {
      if (input === PASSWORD) {
        onAdminChange(true);
      } else {
        setInput("");
      }
      return;
    }
    if (input.length < MAX_LENGTH) {
      setInput(input + key);
    }
  };

  const renderKey = (key: string) => {
    const style = key === "C" ? "C" : key === "E" ? "E" : "";
    return (
      <button key={key} className={`password-key ${style}`} onClick={() => handleKey(key)}>
        {key}
      </button>
    );
  };

  return (
    <div className="password-pad-back">
      <div className="password-pad">
        <div className="password-display">{"*".repeat(input.length)}</div>
        <div className="password-keypad">
          {KEYS.map((key) => renderKey(key))}
        </div>
      </div>
    </div>
  );
}
