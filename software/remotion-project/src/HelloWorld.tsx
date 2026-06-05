import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

export const HelloWorld: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: '#0b0b14', justifyContent: 'center', alignItems: 'center'}}>
      <h1 style={{color: 'white', fontFamily: 'sans-serif', fontSize: 90, opacity}}>
        Executive Agent Workspace
      </h1>
    </AbsoluteFill>
  );
};
