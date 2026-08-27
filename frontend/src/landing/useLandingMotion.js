import { useLayoutEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

function later(ms, bag) {
  return new Promise((resolve) => {
    const id = window.setTimeout(resolve, ms);
    bag.timers.push(id);
  });
}

async function playHeroLoop(rootEl, bag) {
  const work = rootEl.querySelector(".df-work");
  const typed = rootEl.querySelector(".df-typed");
  if (!work || !typed) return;
  const phrase = typed.getAttribute("data-type") || "";
  const rows = [...rootEl.querySelectorAll(".df-scan-row")];

  while (!bag.cancelled) {
    work.dataset.phase = "type";
    rows.forEach((row) => row.classList.remove("is-hot"));
    typed.textContent = "";
    for (let i = 0; i <= phrase.length; i += 1) {
      if (bag.cancelled) return;
      typed.textContent = phrase.slice(0, i);
      await later(38, bag);
    }
    await later(420, bag);
    if (bag.cancelled) return;

    work.dataset.phase = "scan";
    for (const row of rows) {
      if (bag.cancelled) return;
      rows.forEach((item) => item.classList.remove("is-hot"));
      row.classList.add("is-hot");
      await later(720, bag);
    }

    work.dataset.phase = "skel";
    await later(1600, bag);
    if (bag.cancelled) return;

    work.dataset.phase = "insight";
    await later(3400, bag);
  }
}

export default function useLandingMotion(root) {
  const openRef = useRef(0);

  useGSAP(
    (context, contextSafe) => {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const typed = root.current?.querySelector(".df-typed");
      const accCleanups = [];

      if (reduce) {
        gsap.set(
          ".df-hero-sub, .df-hero-cta, .df-hero-stage, .df-panel, .df-manifesto p, .df-scan-row, .df-skel, .df-insight, .df-reveal",
          { clearProps: "all", opacity: 1, y: 0, visibility: "visible" }
        );
        if (typed) typed.textContent = typed.getAttribute("data-type") || "";
      } else {
        gsap.from(".df-hero-sub", {
          y: 14,
          opacity: 0,
          duration: 0.85,
          delay: 0.22,
          ease: "power3.out",
        });
        gsap.from(".df-hero-cta", {
          y: 10,
          opacity: 0,
          duration: 0.75,
          delay: 0.18,
          ease: "power3.out",
        });
        gsap.from(".df-hero-stage", {
          y: 48,
          opacity: 0,
          duration: 1.15,
          delay: 0.24,
          ease: "power3.out",
        });

        const bag = { cancelled: false, timers: [] };
        if (root.current) playHeroLoop(root.current, bag);
        accCleanups.push(() => {
          bag.cancelled = true;
          bag.timers.forEach((id) => window.clearTimeout(id));
        });

        gsap.utils.toArray(".df-reveal").forEach((section) => {
          const kids = Array.from(section.children);
          gsap.from(kids, {
            y: 72,
            opacity: 0,
            duration: 1.05,
            stagger: 0.14,
            ease: "power3.out",
            scrollTrigger: {
              trigger: section,
              start: "top 84%",
              once: true,
            },
          });
        });

        gsap.from(".df-panel", {
          y: 80,
          opacity: 0,
          duration: 1,
          stagger: 0.16,
          ease: "power3.out",
          scrollTrigger: {
            trigger: ".df-panels",
            start: "top 82%",
            once: true,
          },
        });

        gsap.from(".df-split-art", {
          x: -40,
          opacity: 0,
          duration: 1.1,
          ease: "power3.out",
          scrollTrigger: {
            trigger: ".df-split",
            start: "top 78%",
            once: true,
          },
        });

        gsap.from(".df-orbit", {
          scale: 0.92,
          opacity: 0,
          duration: 1.1,
          ease: "power3.out",
          scrollTrigger: {
            trigger: ".df-split-art",
            start: "top 75%",
            once: true,
          },
        });

        gsap.utils.toArray(".df-manifesto p").forEach((p) => {
          gsap
            .timeline({
              scrollTrigger: {
                trigger: p,
                start: "top 88%",
                end: "bottom 18%",
                scrub: 0.7,
              },
            })
            .fromTo(
              p,
              { opacity: 0.12, y: 36 },
              { opacity: 1, y: 0, ease: "none", duration: 0.5 }
            )
            .to(p, { opacity: 0.12, y: -18, ease: "none", duration: 0.5 });
        });

        gsap.from(".df-local-grid article", {
          y: 40,
          opacity: 0,
          stagger: 0.12,
          duration: 0.9,
          ease: "power3.out",
          scrollTrigger: {
            trigger: ".df-local-grid",
            start: "top 82%",
            once: true,
          },
        });

        gsap.from(".df-faq-item", {
          y: 24,
          opacity: 0,
          stagger: 0.08,
          duration: 0.7,
          ease: "power3.out",
          scrollTrigger: {
            trigger: ".df-faq",
            start: "top 80%",
            once: true,
          },
        });
      }

      const items = gsap.utils.toArray(".df-acc-item");
      if (items.length) {
        const setOpen = contextSafe((index) => {
          items.forEach((el, i) => el.classList.toggle("is-open", i === index));
        });
        setOpen(0);
        items.forEach((el, i) => {
          const btn = el.querySelector(".df-acc-head");
          if (!btn) return;
          const onClick = contextSafe(() => {
            openRef.current = i;
            setOpen(i);
          });
          btn.addEventListener("click", onClick);
          accCleanups.push(() => btn.removeEventListener("click", onClick));
        });
      }

      return () => accCleanups.forEach((fn) => fn());
    },
    { scope: root }
  );
}

export function useLandingBodyClass() {
  useLayoutEffect(() => {
    document.documentElement.classList.add("is-landing");
    document.body.classList.add("is-landing");
    return () => {
      document.documentElement.classList.remove("is-landing");
      document.body.classList.remove("is-landing");
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
      window.scrollTo(0, 0);
    };
  }, []);
}
