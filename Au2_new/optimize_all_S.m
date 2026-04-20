function [coeff_opt, resnorm] = optimize_all_S(co,fn1,fn2,fn3,fn4,fn5,fchd)

nv = 50;

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Transfer
IdVg1=abs(csvread(fn1));
c=0; %counter
for i=1:length(IdVg1(:,1))
    if IdVg1(i-c,2)==0
        IdVg1(i-c,:)=[]; %deletes terms with no current
        c=c+1;
    end
end
Vg1max = max(IdVg1(:,1));
Vg1min = min(IdVg1(:,1));
Vv(:,1) = linspace(Vg1min,Vg1max,nv)'; 
Id(:,1) = log10(interp1(IdVg1(:,1),IdVg1(:,2),Vv(:,1)));

IdVg2=abs(csvread(fn2));
c=0;
for i=1:length(IdVg2(:,1))
    if IdVg2(i-c,2)==0
        IdVg2(i-c,:)=[]; %deletes terms with no current
        c=c+1;
    end
end
Vg2max = max(IdVg2(:,1));
Vg2min = min(IdVg2(:,1));
Vv(:,2) = linspace(Vg2min,Vg2max,nv)'; 
Id(:,2) = log10(interp1(IdVg2(:,1),IdVg2(:,2),Vv(:,2)));


% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Output
IdVd1=csvread(fn3);
c=0;
for i=1:length(IdVd1(:,1))
    if IdVd1(i-c,2)<=0
        IdVd1(i-c,:)=[]; %deletes terms with no current
        c=c+1;
    end
end

% Zero current at zero voltage
Vo = IdVd1(1,1);
IdVd1(:,1) = IdVd1(:,1) - Vo;

Vd1max = max(IdVd1(:,1));
Vd1min = min(IdVd1(:,1));
Vv(:,3) = linspace(Vd1min,Vd1max,nv)'; 
Id(:,3) = interp1(IdVd1(:,1),IdVd1(:,2),Vv(:,3));

IdVd2=csvread(fn4);
c=0;
for i=1:length(IdVd2(:,1))
    if IdVd2(i-c,2)<=0
        IdVd2(i-c,:)=[]; %deletes terms with no current
        c=c+1;
    end
end

% Zero current at zero voltage
Vo = IdVd2(1,1);
IdVd2(:,1) = IdVd2(:,1) - Vo;

Vd2max = max(IdVd2(:,1));
Vd2min = min(IdVd2(:,1));
Vv(:,4) = linspace(Vd2min,Vd2max,nv)'; 
Id(:,4) = interp1(IdVd2(:,1),IdVd2(:,2),Vv(:,4));


IdVd3=csvread(fn5);
c=0;
for i=1:length(IdVd3(:,1))
    if IdVd3(i-c,2)<=0
        IdVd3(i-c,:)=[]; %deletes terms with no current
        c=c+1;
    end
end

% Zero current at zero voltage
Vo = IdVd3(1,1);
IdVd3(:,1) = IdVd3(:,1) - Vo;

Vd3max = max(IdVd3(:,1));
Vd3min = min(IdVd3(:,1));
Vv(:,5) = linspace(Vd3min,Vd3max,nv)'; 
Id(:,5) = interp1(IdVd3(:,1),IdVd3(:,2),Vv(:,5));


% options = optimset('Display','iter','TolFun',1e-11);
options = optimset('Display','iter','TolFun',1e-4,'MaxFunEvals',10000);
% [Vtho, delta, n, l, lam, Vgcrit, Jth, Rso, Vtun, V0, Rmax]
lb = [10; 0.01; 1e1; 1; 1e4; 1;  1e-6; 0e0; 1e0; 2; 2e7]; % lower bound constraints
ub = [24; 0.10; 1e2; 4; 1e6; 26; 1e-4; 1e0; 5e0; 8; 6e7]; % upper bound constraints

coeff_opt = co;
[coeff_opt, resnorm] = lsqcurvefit(fchd,co,Vv,Id,lb,ub,options); 



end