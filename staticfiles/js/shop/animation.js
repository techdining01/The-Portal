gsap.from("h1, h2, h3", {
    duration: 1,
    y: -40,
    opacity: 0,
    ease: "power3.out"
});

gsap.from(".card", {
    scrollTrigger: ".card",
    duration: 1,
    y: 40,
    opacity: 0,
    stagger: 0.2
});
