"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FiArrowLeft } from "react-icons/fi";

import { useProduct } from "@/features/products/hooks/useProduct";
import { mapApiProductToProduct } from "@/features/products/data/productAdapter";
import CustomizationForm from "./CustomizationForm";

export default function ProductPage() {
  const params = useParams();

  const slug = String(params.slug);

  const {
    data: apiProduct,
    isLoading,
    isError,
  } = useProduct(slug);

  if (isLoading) {
    return (
      <main className="kc-product-page">
        <div className="kc-container">
          <div className="kc-product-loading">
            Loading product...
          </div>
        </div>
      </main>
    );
  }

  if (isError || !apiProduct) {
    return (
      <main className="kc-product-page">
        <div className="kc-container">
          <div className="kc-product-error">
            <h1>
              Product not found
            </h1>

            <p>
              We couldn&apos;t find the keepsake
              you&apos;re looking for.
            </p>

            <Link
              href="/#shop"
              className="kc-btn kc-btn-outline"
            >
              <FiArrowLeft size={17} />
              Back to collection
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const product =
    mapApiProductToProduct(apiProduct);

  const images = apiProduct.images || [];

  return (
    <main className="kc-product-page">

      {/* Back link */}
      <div className="kc-container">
        <Link
          href="/#shop"
          className="kc-product-back"
        >
          <FiArrowLeft size={17} />
          Back to collection
        </Link>
      </div>

      <section className="kc-section">
        <div className="kc-container">

          <div className="kc-product-layout">

            {/* Product images */}
            <div className="kc-product-gallery">

              <div className="kc-product-main-image">

                {product.primaryImage ? (
                  <img
                    src={product.primaryImage}
                    alt={product.name}
                  />
                ) : (
                  <div className="kc-product-placeholder">
                    Product image
                  </div>
                )}

                {product.badge && (
                  <span className="kc-product-badge">
                    {product.badge}
                  </span>
                )}
              </div>

              {images.length > 1 && (
                <div className="kc-product-thumbnails">
                  {images.map((image) => (
                    <div
                      key={image.id}
                      className="kc-product-thumbnail"
                    >
                      <img
                        src={image.image}
                        alt={
                          image.alt_text ||
                          product.name
                        }
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Product information */}
            <div className="kc-product-info">

              <span className="kc-product-craft">
                {product.craft === "embroidery"
                  ? "Embroidery"
                  : product.craft ===
                    "wood-leather"
                  ? "Wood & Leather"
                  : "Metal Jewelry"}
              </span>

              <h1>
                {product.name}
              </h1>

              <div className="kc-product-price">
                KSh{" "}
                {product.price.toLocaleString(
                  "en-KE"
                )}
              </div>

              <p className="kc-product-description">
                {product.description}
              </p>

              <CustomizationForm
                product={product}
              />

            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
