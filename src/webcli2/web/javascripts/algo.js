export function getNextValue({values, startValue=1, stepValue=1}) {
    /***************
     * Given an array of numbers in values, find the next value
     * If values is empty, i returns startValue, otherwise, returns max value plus step
     */
    if (values.length == 0) {
        return startValue;
    }
    return stepValue + _.max(values);
}

export function dropItemFromReactState({element, stateFieldName, shouldRemove}) {
    /***************
     * remove array item from a react element's state field
     * element: the react element
     * stateFieldName: the state field name
     * shouldRemove: a callback to decide if we should remove the item
     */
    const newValues = element.state[stateFieldName].filter(
        element => !shouldRemove(element)
    );
    element.setState({
        [stateFieldName]:newValues
    });
}

export function updateMatchingItemsFromReactState({element, stateFieldName, shouldUpdate, doUpdate}) {
    const newValues = element.state[stateFieldName].map(
        item => {
            if (!shouldUpdate(item)) {
                return item;
            }
            doUpdate(item);
            return item;
        }
    );
    element.setState({
        [stateFieldName]:newValues
    });
}

export async function updateMatchingItemsFromReactStateAsync({element, stateFieldName, shouldUpdate, doUpdate}) {
    const newValues = [];
    for (const item of element.state[stateFieldName]) {
        const willUpdate = await shouldUpdate(item);
        if (!willUpdate) {
            newValues.push(item);
            continue;
        }
        await doUpdate(item);
        newValues.push(item);
    }
    element.setState({
        [stateFieldName]:newValues
    });
}