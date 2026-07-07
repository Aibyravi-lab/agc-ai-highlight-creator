import type { RazorpayOrder, RazorpayPaymentSuccess } from "../types/payment";

interface RazorpayCheckoutOptions {
  key: string;
  amount: number;
  currency: string;
  order_id: string;
  name: string;
  description?: string;
  handler: (response: RazorpayPaymentSuccess) => void;
  modal?: { ondismiss?: () => void };
  theme?: { color?: string };
}

interface RazorpayFailureResponse {
  error?: { description?: string };
}

interface RazorpayCheckoutInstance {
  open: () => void;
  on: (
    event: "payment.failed",
    handler: (response: RazorpayFailureResponse) => void
  ) => void;
}

declare global {
  interface Window {
    Razorpay: new (options: RazorpayCheckoutOptions) => RazorpayCheckoutInstance;
  }
}

const RAZORPAY_SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";

let scriptLoadPromise: Promise<void> | null = null;

function loadRazorpayScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Razorpay checkout is only available in the browser"));
  }
  if (window.Razorpay) return Promise.resolve();
  if (scriptLoadPromise) return scriptLoadPromise;

  scriptLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = RAZORPAY_SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptLoadPromise = null;
      reject(new Error("Failed to load Razorpay checkout. Please try again."));
    };
    document.body.appendChild(script);
  });

  return scriptLoadPromise;
}

interface OpenCheckoutCallbacks {
  onSuccess: (payment: RazorpayPaymentSuccess) => void;
  onCancel: () => void;
  onFailure: (reason: string) => void;
}

export async function openRazorpayCheckout(
  order: RazorpayOrder,
  callbacks: OpenCheckoutCallbacks
): Promise<void> {
  await loadRazorpayScript();

  const checkout = new window.Razorpay({
    key: order.key_id,
    amount: order.amount,
    currency: order.currency,
    order_id: order.order_id,
    name: "Vedzovi",
    description: "Vedzovi Pro Subscription",
    handler: (response) => callbacks.onSuccess(response),
    modal: {
      ondismiss: () => callbacks.onCancel(),
    },
    theme: { color: "#16a34a" },
  });

  checkout.on("payment.failed", (response) => {
    callbacks.onFailure(response?.error?.description || "Payment failed. Please try again.");
  });

  checkout.open();
}
