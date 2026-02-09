"""
Numerical integrators for ODEs (Ordinary Differential Equations).

Story 2.3: RK4 Integration
Implements Euler and Runge-Kutta 4th order integrators.
"""
from typing import List, Callable, Tuple


# Type aliases for clarity
State = List[float]
DerivativeFunction = Callable[[State, float], State]


class EulerIntegrator:
    """
    Euler's method (first-order integrator).
    
    Simple but less accurate than RK4. Included for comparison.
    
    Formula:
        y_{n+1} = y_n + dt * f(y_n, t_n)
    
    Where:
    - y_n = state at step n
    - f = derivative function
    - dt = timestep
    
    Example:
        >>> def derivative(state, t):
        ...     return [state[0]]  # dy/dt = y
        >>> euler = EulerIntegrator()
        >>> state, times = euler.integrate(derivative, [1.0], 0.0, 1.0, 0.1)
    """
    
    def step(
        self,
        derivative: DerivativeFunction,
        state: State,
        t: float,
        dt: float
    ) -> State:
        """
        Perform one Euler step.
        
        Args:
            derivative: Function f(state, t) returning dstate/dt
            state: Current state
            t: Current time
            dt: Timestep
        
        Returns:
            New state after one step
        """
        # Evaluate derivative
        dstate = derivative(state, t)
        
        # Euler step: y_new = y + dt * dy/dt
        state_new = [
            state[i] + dt * dstate[i]
            for i in range(len(state))
        ]
        
        return state_new
    
    def integrate(
        self,
        derivative: DerivativeFunction,
        state0: State,
        t0: float,
        t_end: float,
        dt: float
    ) -> Tuple[State, List[float]]:
        """
        Integrate from t0 to t_end.
        
        Args:
            derivative: Derivative function
            state0: Initial state
            t0: Start time
            t_end: End time
            dt: Timestep
        
        Returns:
            (final_state, time_array)
        """
        state = state0[:]
        t = t0
        times = [t]
        
        while t < t_end:
            # Don't overshoot t_end
            step_dt = min(dt, t_end - t)
            
            state = self.step(derivative, state, t, step_dt)
            t += step_dt
            times.append(t)
        
        return state, times


class RK4Integrator:
    """
    Runge-Kutta 4th order integrator.
    
    Fourth-order accurate method. Error scales as O(dt⁴).
    Much more accurate than Euler for same timestep.
    
    Formula:
        k1 = f(y_n, t_n)
        k2 = f(y_n + dt/2 * k1, t_n + dt/2)
        k3 = f(y_n + dt/2 * k2, t_n + dt/2)
        k4 = f(y_n + dt * k3, t_n + dt)
        
        y_{n+1} = y_n + dt/6 * (k1 + 2k2 + 2k3 + k4)
    
    Properties:
    - 4th order accurate (error ~ dt⁴)
    - 4 function evaluations per step
    - 2-3x slower than Euler, but can use 10x larger timestep
    
    Example:
        >>> def derivative(state, t):
        ...     x, v = state
        ...     return [v, -x]  # Harmonic oscillator
        >>> rk4 = RK4Integrator()
        >>> state, times = rk4.integrate(derivative, [1.0, 0.0], 0.0, 10.0, 0.1)
    """
    
    def step(
        self,
        derivative: DerivativeFunction,
        state: State,
        t: float,
        dt: float
    ) -> State:
        """
        Perform one RK4 step.
        
        Args:
            derivative: Function f(state, t) returning dstate/dt
            state: Current state
            t: Current time
            dt: Timestep
        
        Returns:
            New state after one step
        """
        n = len(state)
        
        # k1 = f(y_n, t_n)
        k1 = derivative(state, t)
        
        # k2 = f(y_n + dt/2 * k1, t_n + dt/2)
        state_k2 = [state[i] + 0.5 * dt * k1[i] for i in range(n)]
        k2 = derivative(state_k2, t + 0.5 * dt)
        
        # k3 = f(y_n + dt/2 * k2, t_n + dt/2)
        state_k3 = [state[i] + 0.5 * dt * k2[i] for i in range(n)]
        k3 = derivative(state_k3, t + 0.5 * dt)
        
        # k4 = f(y_n + dt * k3, t_n + dt)
        state_k4 = [state[i] + dt * k3[i] for i in range(n)]
        k4 = derivative(state_k4, t + dt)
        
        # y_{n+1} = y_n + dt/6 * (k1 + 2k2 + 2k3 + k4)
        state_new = [
            state[i] + (dt / 6.0) * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i])
            for i in range(n)
        ]
        
        return state_new
    
    def integrate(
        self,
        derivative: DerivativeFunction,
        state0: State,
        t0: float,
        t_end: float,
        dt: float
    ) -> Tuple[State, List[float]]:
        """
        Integrate from t0 to t_end using RK4.
        
        Args:
            derivative: Derivative function
            state0: Initial state
            t0: Start time
            t_end: End time
            dt: Timestep
        
        Returns:
            (final_state, time_array)
        """
        state = state0[:]
        t = t0
        times = [t]
        
        while t < t_end:
            # Don't overshoot t_end
            step_dt = min(dt, t_end - t)
            
            state = self.step(derivative, state, t, step_dt)
            t += step_dt
            times.append(t)
        
        return state, times
    
    def integrate_with_history(
        self,
        derivative: DerivativeFunction,
        state0: State,
        t0: float,
        t_end: float,
        dt: float
    ) -> Tuple[List[State], List[float]]:
        """
        Integrate and return full history of states.
        
        Useful for plotting trajectories.
        
        Args:
            derivative: Derivative function
            state0: Initial state
            t0: Start time
            t_end: End time
            dt: Timestep
        
        Returns:
            (state_history, time_array)
            
        Example:
            >>> states, times = rk4.integrate_with_history(...)
            >>> for state, t in zip(states, times):
            ...     print(f"At t={t}: state={state}")
        """
        state = state0[:]
        t = t0
        
        states = [state[:]]
        times = [t]
        
        while t < t_end:
            step_dt = min(dt, t_end - t)
            
            state = self.step(derivative, state, t, step_dt)
            t += step_dt
            
            states.append(state[:])
            times.append(t)
        
        return states, times
