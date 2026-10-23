/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CableCuttingDialog extends Component {
    static template = "website_nexconect.CableCuttingDialog";
    static components = { Dialog };

    setup() {
        this.state = useState({
            lines: [
                {
                    pieces: 1,
                    length: 0,
                },
            ],
            error: "",
        });
    }

    addLine() {
        this.state.lines.push({
            pieces: 1,
            length: 0,
        });
    }

    removeLine(index) {
        this.state.lines.splice(index, 1);
        this.state.error = "";
    }

    updateLine(index, field, value) {
        const val = parseFloat(value || 0);
        this.state.lines[index][field] = val;
        this.state.error = "";
    }

    getLineTotal(line) {
        return (parseFloat(line.pieces || 0) * parseFloat(line.length || 0));
    }

    get grandTotal() {
        return this.state.lines.reduce((total, line) => {
            return total + this.getLineTotal(line);
        }, 0);
    }

    get totalPieces() {
        return this.state.lines.reduce((total, line) => {
            return total + parseFloat(line.pieces || 0);
        }, 0);
    }

    confirm() {
        const validLines = [];

        for (const line of this.state.lines) {
            const pieces = parseFloat(line.pieces || 0);
            const length = parseFloat(line.length || 0);
            console.log("\n\nline::::::", line)

            if (pieces <= 0 || length <= 0) {
                this.state.error = "Pieces and length must be greater than 0.";
                return;
            }

            validLines.push({
                pieces: pieces,
                length: length,
                total_length: pieces * length,
            });
        }

        if (!validLines.length || this.grandTotal <= 0) {
            this.state.error = "Please add at least one valid cutting line.";
            return;
        }

        this.props.confirm({
            lines: validLines,
            total_length: this.grandTotal,
            total_pieces: this.totalPieces,
        });

        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
