export interface RazorpayOrder {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
}

export interface RazorpayPaymentSuccess {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}
