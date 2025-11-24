function searchStudent(q){
    fetch("/shop/api/student/search/?q=" + q)
    .then(r => r.json())
    .then(data => {
        console.log(data);
    });
}
