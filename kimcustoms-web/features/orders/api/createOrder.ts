import axios from "axios";

import type { CartItem } from "@/features/cart/types/cart";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export interface CreateOrderData {
  firstName: string;
  lastName: string;
  phone: string;
  email: string;

  county: string;
  town: string;
  address: string;
  notes: string;

  paymentMethod:
    | "mpesa"
    | "card"
    | "cash";

  items: CartItem[];
}

export interface CreateOrderResponse {
  order_number: string;
  status: string;
  subtotal: string;
  delivery_fee: string;
  total: string;
  created_at: string;
  // Short-lived bearer token, retained only in checkout component memory.
  payment_token: string;
}

export async function createOrder(
  data: CreateOrderData
): Promise<CreateOrderResponse> {
  const response = await axios.post<CreateOrderResponse>(
    `${API_URL}/api/orders/`,
    {
      first_name: data.firstName,
      last_name: data.lastName,
      phone: data.phone,
      email: data.email,

      delivery_address:
        `${data.address}, ${data.town}, ${data.county}`,

      delivery_city: data.town,

      notes: data.notes,

      payment_method:
        data.paymentMethod,

      items: data.items.map((item) => ({
        product_id: Number(item.product.id),
        quantity: item.quantity,
        personalization:
          item.personalization || "",
      })),
    }
  );

  return response.data;
}
