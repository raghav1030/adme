import React from 'react';

type LoaderProps = {
    className?: string;
    size?: number;
};

const Loader = ({ className, size = 256 }: LoaderProps) => {
    const scale = size / 256;

    const lines = [
        { x1: 128 * scale, y1: 32 * scale, x2: 128 * scale, y2: 64 * scale },
        { x1: 195.9 * scale, y1: 60.1 * scale, x2: 173.3 * scale, y2: 82.7 * scale },
        { x1: 224 * scale, y1: 128 * scale, x2: 192 * scale, y2: 128 * scale },
        { x1: 195.9 * scale, y1: 195.9 * scale, x2: 173.3 * scale, y2: 173.3 * scale },
        { x1: 128 * scale, y1: 224 * scale, x2: 128 * scale, y2: 192 * scale },
        { x1: 60.1 * scale, y1: 195.9 * scale, x2: 82.7 * scale, y2: 173.3 * scale },
        { x1: 32 * scale, y1: 128 * scale, x2: 64 * scale, y2: 128 * scale },
        { x1: 60.1 * scale, y1: 60.1 * scale, x2: 82.7 * scale, y2: 82.7 * scale },
    ];

    // Scaled stroke width
    const strokeWidth = 24 * scale;

    return (
        <svg
            className={`animate-spin stroke-black ${className}`}
            viewBox={`0 0 ${size} ${size}`}
            width={size}
            height={size}
        >
            {lines.map(({ x1, y1, x2, y2 }, i) => (
                <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={strokeWidth}
                />
            ))}
        </svg>
    );
};

export default Loader;
