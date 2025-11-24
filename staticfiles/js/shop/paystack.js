document.getElementById("paystack-btn")?.addEventListener("click", function(){
    let email = document.getElementById("pay-email").value;

    fetch("/shop/pay/init/", {
        method: "POST",
        headers: {"X-CSRFToken": getCSRF()},
        body: new URLSearchParams({email})
    })
    .then(r => r.json())
    .then(data => {
        let handler = PaystackPop.setup({
            key: PAYSTACK_PUBLIC_KEY,
            email: email,
            amount: data.data.amount,
            ref: data.data.reference,
            callback: function(){
                window.location.href = "/shop/receipt/" + data.data.reference + "/";
            }
        });
        handler.openIframe();
    });
});
