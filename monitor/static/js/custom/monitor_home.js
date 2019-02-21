$(document).ready(()=>{
	
	$.ajax({
		url: "stream/",
		data : {name: 'working'},
		success: data => {
			console.log(data)
		},
		error: msg => {console.log(msg.responseText) }
	})
})