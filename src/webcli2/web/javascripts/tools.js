export function setStateAsync(component, newState) {
    return new Promise((resolve) => {
        component.setState(newState, () => resolve(component.state));
    });
}
