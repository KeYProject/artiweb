function formatLabel(context) {
    let label = context.dataset.label || '';
    if (label) {
        label += ': ';
    }
    const value = context.raw;
    let format;
    if (value == 0) {
        format = "0s";
    } else if (value < 3) {
        format = Math.round(value * 1000) + "ms";
    } else if (value < 120) {
        format = Math.round(value) + "s";
    } else {
        format = "";
        let remainder = value;
        if (remainder > 3600) {
            const hours = Math.floor(remainder / 3600);
            remainder = remainder % 3600;
            format += hours + "h ";
        }
        
        if (remainder > 60) {
            const minutes = Math.floor(remainder / 60);
            remainder = remainder % 60;
            format += minutes + "m ";
        }
        
        const seconds = Math.round(remainder);
        format += seconds + "s";
    }
    return label + format;
}