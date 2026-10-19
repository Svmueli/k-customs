"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Product } from "@/features/products/data/products";

import type { CartItem } from "../types/cart";

import {
  clearStoredCart,
  getStoredCart,
  saveCart,
} from "../utils/cartStorage";

interface AddToCartOptions {
  product: Product;

  quantity: number;

  personalization: string;

  imageName?: string;

  imagePreview?: string;
}

interface CartNotification {
  productName: string;
}

interface CartContextValue {
  items: CartItem[];

  itemCount: number;

  subtotal: number;

  addToCart: (
    options: AddToCartOptions
  ) => void;

  removeFromCart: (
    id: string
  ) => void;

  updateQuantity: (
    id: string,
    quantity: number
  ) => void;

  clearCart: () => void;

  isCartOpen: boolean;

  openCart: () => void;

  closeCart: () => void;

  toggleCart: () => void;

  notification:
    | CartNotification
    | null;

  dismissNotification: () => void;
}

const CartContext =
  createContext<CartContextValue | null>(
    null
  );

export function CartProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [items, setItems] =
    useState<CartItem[]>([]);

  const [isCartOpen, setIsCartOpen] =
    useState(false);

  const [hydrated, setHydrated] =
    useState(false);

  const [notification, setNotification] =
    useState<CartNotification | null>(
      null
    );

  /*
   * Load cart from localStorage
   * after the browser hydrates.
   */
  useEffect(() => {
    const hydrationTimer = window.setTimeout(() => {
      setItems(getStoredCart());
      setHydrated(true);
    }, 0);

    return () => window.clearTimeout(hydrationTimer);
  }, []);

  /*
   * Save cart whenever it changes.
   */
  useEffect(() => {
    if (!hydrated) {
      return;
    }

    saveCart(items);
  }, [items, hydrated]);

  /*
   * Automatically dismiss the
   * notification after 3.5 seconds.
   */
  useEffect(() => {
    if (!notification) {
      return;
    }

    const timer = window.setTimeout(() => {
      setNotification(null);
    }, 3500);

    return () => {
      window.clearTimeout(timer);
    };
  }, [notification]);

  /*
   * Total number of individual
   * items in the cart.
   *
   * Example:
   *
   * Hoodie × 2
   * Keyring × 1
   *
   * itemCount = 3
   */
  const itemCount = useMemo(() => {
    return items.reduce(
      (total, item) =>
        total + item.quantity,
      0
    );
  }, [items]);

  /*
   * Cart subtotal.
   */
  const subtotal = useMemo(() => {
    return items.reduce(
      (total, item) =>
        total +
        item.product.price *
          item.quantity,
      0
    );
  }, [items]);

  /*
   * Add an item.
   *
   * IMPORTANT:
   *
   * We intentionally DO NOT open
   * the cart drawer here.
   *
   * Instead:
   *
   * 1. Update cart
   * 2. Update Navbar count
   * 3. Show notification
   * 4. Keep customer on product page
   */
  function addToCart({
    product,
    quantity,
    personalization,
    imageName,
    imagePreview,
  }: AddToCartOptions) {
    const newItem: CartItem = {
      id: crypto.randomUUID(),

      product,

      quantity,

      personalization,

      imageName,

      imagePreview,
    };

    setItems((currentItems) => [
      ...currentItems,
      newItem,
    ]);

    setNotification({
      productName: product.name,
    });
  }

  /*
   * Remove item.
   */
  function removeFromCart(id: string) {
    setItems((currentItems) =>
      currentItems.filter(
        (item) => item.id !== id
      )
    );
  }

  /*
   * Update quantity.
   */
  function updateQuantity(
    id: string,
    quantity: number
  ) {
    if (quantity <= 0) {
      removeFromCart(id);

      return;
    }

    setItems((currentItems) =>
      currentItems.map((item) =>
        item.id === id
          ? {
              ...item,
              quantity,
            }
          : item
      )
    );
  }

  /*
   * Empty the entire cart.
   */
  function clearCart() {
    setItems([]);

    clearStoredCart();
  }

  /*
   * Cart drawer controls.
   */
  function openCart() {
    setIsCartOpen(true);
  }

  function closeCart() {
    setIsCartOpen(false);
  }

  function toggleCart() {
    setIsCartOpen(
      (current) => !current
    );
  }

  /*
   * Notification controls.
   */
  function dismissNotification() {
    setNotification(null);
  }

  return (
    <CartContext.Provider
      value={{
        items,

        itemCount,

        subtotal,

        addToCart,

        removeFromCart,

        updateQuantity,

        clearCart,

        isCartOpen,

        openCart,

        closeCart,

        toggleCart,

        notification,

        dismissNotification,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context =
    useContext(CartContext);

  if (!context) {
    throw new Error(
      "useCart must be used inside CartProvider"
    );
  }

  return context;
}
