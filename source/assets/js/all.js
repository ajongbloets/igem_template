//= require jquery
//= require popper
//= require bootstrap-sprockets

// 
// Home
//

// Move the module summaries' height so they match up with the diagonal linear gradient
function setModuleSummaryHeight () {
	var midWidth = document.querySelector('.summary-container#modules > .summary-col-mid').offsetWidth / 2.0;
	var midHeight = document.querySelector('.home-spacer#modules').offsetHeight / 2.0;
	var angle = 25 * Math.PI / 180.0;
    var icons = document.getElementsByClassName('summary-modules-outer');
    console.log("test")
    for (i=0; i<icons.length; i++){
    	icons[i].style["margin-top"] = midHeight - (icons[i].offsetLeft - midWidth) * Math.tan(angle);
    }
};
window.onload = setModuleSummaryHeight;
window.onresize = setModuleSummaryHeight;
