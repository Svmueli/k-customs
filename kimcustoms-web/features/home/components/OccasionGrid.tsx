import {
  FiHeart,
  FiUsers,
  FiAward,
  FiStar,
  FiHome,
  FiGlobe,
} from "react-icons/fi";

const occasions = [
  {
    id: "love",
    title: "Her & Him",
    description: "For the person who makes your heart skip.",
    icon: FiHeart,
  },
  {
    id: "parents",
    title: "Mum & Dad",
    description: "A little piece of home, made to last.",
    icon: FiUsers,
  },
  {
    id: "graduation",
    title: "Graduation",
    description: "Celebrate the journey and everything ahead.",
    icon: FiAward,
  },
  {
    id: "memory",
    title: "In loving memory",
    description: "Keep their story close, always.",
    icon: FiStar,
  },
  {
    id: "wedding",
    title: "Weddings & ruracio",
    description: "Mark the beginning of something beautiful.",
    icon: FiHome,
  },
  {
    id: "diaspora",
    title: "From the diaspora",
    description: "Send a piece of home, wherever they are.",
    icon: FiGlobe,
  },
];

export default function OccasionGrid() {
  return (
    <section
      id="occasions"
      className="kc-section kc-occasions"
      aria-labelledby="occasions-heading"
    >
      <div className="kc-container">
        <div className="kc-section-head kc-occasions-head">
          <span className="kc-eyebrow">Find the right gift</span>

          <h2 id="occasions-heading">
            Made for{" "}
            <span className="kc-em">their moment.</span>
          </h2>

          <p>
            Whether you&apos;re celebrating love, family, achievement or memory,
            start with the occasion and we&apos;ll help you find something
            meaningful.
          </p>
        </div>

        <div className="kc-occasion-grid">
          {occasions.map((occasion) => {
            const Icon = occasion.icon;

            return (
              <a
                key={occasion.id}
                href="shop"
                className="kc-occasion-card"
              >
                <span className="kc-occasion-icon">
                  <Icon size={22} strokeWidth={1.7} />
                </span>

                <span className="kc-occasion-title">
                  {occasion.title}
                </span>

                <span className="kc-occasion-description">
                  {occasion.description}
                </span>

                <span className="kc-occasion-arrow" aria-hidden="true">
                  →
                </span>
              </a>
            );
          })}
        </div>
      </div>
    </section>
  );
}
