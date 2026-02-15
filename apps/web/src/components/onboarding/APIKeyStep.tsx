"use client";

import { useState } from "react";
import { Key, ArrowLeft, ArrowRight, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { API_URL } from "@/lib/cloud-mode";

interface APIKeyStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function APIKeyStep({ onNext, onBack, onSkip }: APIKeyStepProps) {
  const { t } = useTranslation("onboarding");
  const [apiKey, setApiKey] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [validationStatus, setValidationStatus] = useState<"idle" | "valid" | "invalid">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const handleValidate = async () => {
    if (!apiKey.trim()) return;

    setIsValidating(true);
    setValidationStatus("idle");
    setErrorMessage("");

    try {
      const res = await fetch(`${API_URL}/api/auth/validate-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apiKey: apiKey.trim() }),
      });
      if (!res.ok) {
        throw new Error(t("apiKey.validationFailed"));
      }
      setValidationStatus("valid");
    } catch (err) {
      setValidationStatus("invalid");
      setErrorMessage(
        err instanceof Error ? err.message : t("apiKey.validationFailed")
      );
    } finally {
      setIsValidating(false);
    }
  };

  const handleContinue = () => {
    if (validationStatus === "valid") {
      onNext();
    }
  };

  return (
    <div className="flex flex-col items-center px-8 py-6">
      <div className="w-full max-w-lg">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Key className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              {t("apiKey.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("apiKey.description")}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="api-key-input"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {t("apiKey.label")}
            </label>
            <div className="relative">
              <input
                id="api-key-input"
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setValidationStatus("idle");
                  setErrorMessage("");
                }}
                placeholder={t("apiKey.placeholder")}
                className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {validationStatus === "valid" && (
                <CheckCircle2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-green-500" />
              )}
              {validationStatus === "invalid" && (
                <AlertCircle className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-destructive" />
              )}
            </div>
            {errorMessage && (
              <p className="mt-1.5 text-xs text-destructive">{errorMessage}</p>
            )}
            {validationStatus === "valid" && (
              <p className="mt-1.5 text-xs text-green-600">
                {t("apiKey.validationSuccess")}
              </p>
            )}
          </div>

          <button
            onClick={handleValidate}
            disabled={!apiKey.trim() || isValidating}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isValidating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t("apiKey.validating")}
              </>
            ) : (
              t("apiKey.validate")
            )}
          </button>

          <p className="text-xs text-muted-foreground">
            {t("apiKey.securityNote")}
          </p>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {t("actions.back")}
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onSkip}
              className="rounded-md px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {t("actions.skipForNow")}
            </button>
            <button
              onClick={handleContinue}
              disabled={validationStatus !== "valid"}
              className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("actions.continue")}
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
