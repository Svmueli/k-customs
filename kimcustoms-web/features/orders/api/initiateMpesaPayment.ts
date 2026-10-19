import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface MpesaStkPushResponse {
  attempt_id: number;
  status: string;
  checkout_request_id: string | null;
}

export async function initiateMpesaPayment(
  paymentToken: string,
  phoneNumber: string
): Promise<MpesaStkPushResponse> {
  const response = await axios.post<MpesaStkPushResponse>(
    `${API_URL}/api/payments/mpesa/stk-push/`,
    { payment_token: paymentToken, phone_number: phoneNumber },
    {
      // This is request uniqueness, not a credential. The payment token never
      // enters localStorage.
      headers: { "Idempotency-Key": crypto.randomUUID() },
    }
  );

  return response.data;
}
