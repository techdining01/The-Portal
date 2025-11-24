document.addEventListener("click", function(e){
    if(e.target.classList.contains("add-cart")){
        let id = e.target.dataset.id;

        fetch("/shop/cart/add/", {
            method: "POST",
            headers: {"X-CSRFToken": getCSRF()},
            body: new URLSearchParams({product_id: id})
        }).then(r => r.json()).then(data => {
            alert("Added to cart!");
        });
    }
});

function getCSRF(){
    return document.cookie.split("csrftoken=")[1];
}
