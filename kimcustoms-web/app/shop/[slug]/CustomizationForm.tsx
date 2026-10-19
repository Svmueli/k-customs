"use client";

import {
  ChangeEvent,
  FormEvent,
  useRef,
  useState,
} from "react";

import {
  FiCheck,
  FiHeart,
  FiUpload,
  FiX,
} from "react-icons/fi";

import type { Product } from "@/features/products/data/products";

import { useCart } from "@/features/cart/context/CartContext";

interface CustomizationFormProps {
  product: Product;
}

export default function CustomizationForm({
  product,
}: CustomizationFormProps) {
  const fileInputRef =
    useRef<HTMLInputElement>(null);

  const { addToCart } = useCart();

  const [fileName, setFileName] =
    useState("");

  const [message, setMessage] =
    useState("");

  const [quantity, setQuantity] =
    useState(1);

  const [error, setError] =
    useState("");

  /* --------------------------------
     Handle image upload
  -------------------------------- */

  const handleFileChange = (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    setFileName(file.name);

    setError("");
  };

  /* --------------------------------
     Remove uploaded image
  -------------------------------- */

  const removeFile = () => {
    setFileName("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  /* --------------------------------
     Handle quantity
  -------------------------------- */

  const decreaseQuantity = () => {
    setQuantity((current) =>
      Math.max(1, current - 1)
    );
  };

  const increaseQuantity = () => {
    setQuantity((current) =>
      current + 1
    );
  };

  /* --------------------------------
     Add product to cart
  -------------------------------- */

  const handleAddToCart = (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setError("");

    /*
     * We don't require personalization
     * or an image because different
     * KimCustoms products may have
     * different customization requirements.
     */

    addToCart({
      product,
      quantity,
      personalization:
        message.trim(),
      imageName:
        fileName || undefined,
    });

    /*
     * Reset the form after adding.
     *
     * The customer remains on the
     * product page and can continue
     * shopping.
     */

    setMessage("");

    setFileName("");

    setQuantity(1);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <form
      className="kc-customization-form"
      onSubmit={handleAddToCart}
    >
      {/* =================================
          PERSONALIZATION
      ================================= */}

      <div className="kc-form-section">
        <div className="kc-form-heading">
          <span className="kc-form-step">
            1
          </span>

          <div>
            <h2>
              Make it personal
            </h2>

            <p>
              Tell us what you&apos;d like us
              to create.
            </p>
          </div>
        </div>

        <label
          htmlFor="personalization"
          className="kc-form-label"
        >
          Personalization
        </label>

        <textarea
          id="personalization"
          name="personalization"
          value={message}
          onChange={(event) =>
            setMessage(
              event.target.value
            )
          }
          placeholder={
            "e.g. Add the name 'Mum' and the date 12.08.2026..."
          }
          rows={4}
        />

        <span className="kc-form-hint">
          Include names, dates,
          handwriting, coordinates or
          any other details relevant to
          your design.
        </span>
      </div>

      {/* =================================
          IMAGE UPLOAD
      ================================= */}

      <div className="kc-form-section">
        <div className="kc-form-heading">
          <span className="kc-form-step">
            2
          </span>

          <div>
            <h2>
              Upload your photo
            </h2>

            <p>
              Use a clear, high-quality
              image where possible.
            </p>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          id="product-image"
          name="product-image"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          hidden
        />

        {!fileName ? (
          <button
            type="button"
            className="kc-upload-box"
            onClick={() =>
              fileInputRef.current?.click()
            }
          >
            <span className="kc-upload-icon">
              <FiUpload size={22} />
            </span>

            <strong>
              Upload your photo
            </strong>

            <span>
              JPG, PNG or WebP
            </span>
          </button>
        ) : (
          <div className="kc-uploaded-file">
            <div>
              <FiCheck size={18} />

              <span>
                {fileName}
              </span>
            </div>

            <button
              type="button"
              onClick={removeFile}
              aria-label="Remove uploaded image"
            >
              <FiX size={17} />
            </button>
          </div>
        )}
      </div>

      {/* =================================
          QUANTITY
      ================================= */}

      <div className="kc-form-section">
        <div className="kc-form-heading">
          <span className="kc-form-step">
            3
          </span>

          <div>
            <h2>
              Quantity
            </h2>

            <p>
              How many would you like?
            </p>
          </div>
        </div>

        <div
          className="kc-quantity"
          aria-label="Product quantity"
        >
          <button
            type="button"
            onClick={
              decreaseQuantity
            }
            aria-label="Decrease quantity"
          >
            −
          </button>

          <span
            aria-live="polite"
          >
            {quantity}
          </span>

          <button
            type="button"
            onClick={
              increaseQuantity
            }
            aria-label="Increase quantity"
          >
            +
          </button>
        </div>
      </div>

      {/* =================================
          ERROR
      ================================= */}

      {error && (
        <div
          className="kc-form-error"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* =================================
          ADD TO CART
      ================================= */}

      <div className="kc-add-to-cart-area">
        <div className="kc-total">
          <span>
            Total
          </span>

          <strong>
            KSh{" "}
            {(
              product.price *
              quantity
            ).toLocaleString(
              "en-KE"
            )}
          </strong>
        </div>

        <button
          type="submit"
          className="kc-btn kc-btn-rose kc-add-to-cart"
        >
          Add to cart
        </button>

        <button
          type="button"
          className="kc-wishlist"
          aria-label={`Add ${product.name} to wishlist`}
        >
          <FiHeart size={18} />
        </button>
      </div>

      <p className="kc-customization-note">
        Your uploaded photo and
        personalization details will be
        securely attached to your order
        during checkout.
      </p>
    </form>
  );
}
